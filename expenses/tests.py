from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Group, Member, Expense


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpassword123")

    def test_valid_login_returns_token(self):
        response = self.client.post("/api/token/", {"username":"testuser","password":"testpassword123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_registration_returns_token(self):
        response = self.client.post("/api/register/", {"username":"newuser","password":"simple","confirm_password":"simple"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post("/api/register/", {"username":"newuser","password":"one","confirm_password":"two"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_duplicate_username(self):
        response = self.client.post("/api/register/", {"username":"TESTUSER","password":"simple","confirm_password":"simple"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_login_rejected(self):
        response = self.client.post("/api/token/", {"username":"testuser","password":"wrongpassword"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WorkflowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpassword123")
        self.other = User.objects.create_user(username="other", password="testpassword123")
        self.client.force_authenticate(user=self.user)
        self.group = Group.objects.create(name="Apartment", owner=self.user)
        self.alice = Member.objects.create(group=self.group, name="Alice", user=self.user)
        self.bob = Member.objects.create(group=self.group, name="Bob")

    def test_group_can_have_non_user_members(self):
        response = self.client.post("/api/groups/", {"name":"Trip","member_names":["Alice","Jordan","Sam"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual([m["name"] for m in response.data["members"]], ["Alice","Jordan","Sam"])

    def test_groups_are_isolated_by_owner(self):
        Group.objects.create(name="Private", owner=self.other)
        names = [g["name"] for g in self.client.get("/api/groups/").data]
        self.assertNotIn("Private", names)

    def test_expense_crud_and_debt(self):
        create = self.client.post("/api/expenses/", {"group":self.group.id,"description":"Dinner","amount":"60.00","paid_by":self.alice.id,"participants":[self.alice.id,self.bob.id]}, format="json")
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        expense_id = create.data["id"]
        patch = self.client.patch(f"/api/expenses/{expense_id}/", {"description":"Dinner out"}, format="json")
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        debt = self.client.get(f"/api/groups/{self.group.id}/debts/").data[0]
        self.assertEqual(debt["from"], "Bob")
        self.assertEqual(debt["to"], "Alice")
        self.assertEqual(debt["amount"], 30.00)
        self.assertEqual(self.client.delete(f"/api/expenses/{expense_id}/").status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_use_member_from_another_group(self):
        other_group = Group.objects.create(name="Other", owner=self.user)
        outsider = Member.objects.create(group=other_group, name="Outsider")
        response = self.client.post("/api/expenses/", {"group":self.group.id,"description":"Dinner","amount":"20.00","paid_by":self.alice.id,"participants":[self.alice.id,outsider.id]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_group_update_and_delete(self):
        response = self.client.patch(f"/api/groups/{self.group.id}/", {"name":"Home","member_names":["Alice","Bob","Charlie"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Home")
        self.assertEqual(len(response.data["members"]), 3)
        self.assertEqual(self.client.delete(f"/api/groups/{self.group.id}/").status_code, status.HTTP_204_NO_CONTENT)

    def test_group_delete_cascades_expenses_with_protected_members(self):
        expense = Expense.objects.create(
            group=self.group,
            description="Dinner",
            amount="60.00",
            paid_by=self.alice,
        )
        expense.participants.set([self.alice, self.bob])

        response = self.client.delete(f"/api/groups/{self.group.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group.objects.filter(pk=self.group.id).exists())
        self.assertFalse(Expense.objects.filter(pk=expense.id).exists())
        self.assertFalse(Member.objects.filter(group_id=self.group.id).exists())

    def test_group_details(self):
        Expense.objects.create(group=self.group, description="Dinner", amount="60.00", paid_by=self.alice).participants.set([self.alice,self.bob])
        response = self.client.get(f"/api/groups/{self.group.id}/details/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("balances", response.data)
        self.assertIn("debts", response.data)
        self.assertIn("expenses", response.data)


    def test_my_balance_uses_explicit_member_link_when_name_differs_from_username(self):
        trip = Group.objects.create(name="Trip", owner=self.user)
        alex = Member.objects.create(group=trip, name="Alex")
        muhtasim = Member.objects.create(group=trip, name="Muhtasim", user=self.user)
        expense = Expense.objects.create(group=trip, description="Hotel", amount="200.00", paid_by=alex)
        expense.participants.set([alex, muhtasim])

        response = self.client.get("/api/groups/my-balance/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["owed"], 0)
        self.assertEqual(response.data["owe"], 100)

    def test_group_owner_can_choose_not_to_be_a_member(self):
        response = self.client.post("/api/groups/", {
            "name": "Managed group",
            "member_names": ["Alex", "Jordan"],
            "current_member_name": "",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(Member.objects.filter(group_id=response.data["id"], user=self.user).exists())

    def test_group_update_can_change_current_member_identity(self):
        response = self.client.patch(f"/api/groups/{self.group.id}/", {
            "member_names": ["Alice", "Bob"],
            "current_member_name": "Bob",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(Member.objects.get(pk=self.alice.pk).user_id)
        self.assertEqual(Member.objects.get(pk=self.bob.pk).user_id, self.user.id)

    def test_group_update_can_remove_current_member_identity(self):
        response = self.client.patch(f"/api/groups/{self.group.id}/", {
            "member_names": ["Alice", "Bob"],
            "current_member_name": "",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Member.objects.filter(group=self.group, user=self.user).exists())

    def test_group_can_explicitly_link_current_member(self):
        response = self.client.post("/api/groups/", {
            "name": "Trip",
            "member_names": ["Alex", "Muhtasim"],
            "current_member_name": "Muhtasim",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member = Member.objects.get(group_id=response.data["id"], name="Muhtasim")
        self.assertEqual(member.user_id, self.user.id)

    def test_custom_split_and_settlement_updates_balance(self):
        created = self.client.post("/api/expenses/", {
            "group": self.group.id, "description": "Groceries", "amount": "60.00",
            "paid_by": self.alice.id, "participants": [self.alice.id, self.bob.id],
            "split_mode": "custom", "split_values": {str(self.alice.id): "10.00", str(self.bob.id): "50.00"},
            "category": "Food",
        }, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.client.get(f"/api/groups/{self.group.id}/debts/").data[0]["amount"], 50.0)
        settlement = self.client.post("/api/settlements/", {
            "group": self.group.id, "paid_by": self.bob.id, "paid_to": self.alice.id,
            "amount": "20.00",
        }, format="json")
        self.assertEqual(settlement.status_code, 201, settlement.data)
        self.assertEqual(self.client.get(f"/api/groups/{self.group.id}/debts/").data[0]["amount"], 30.0)
        analytics = self.client.get(f"/api/groups/{self.group.id}/analytics/")
        self.assertEqual(analytics.data["categories"][0]["name"], "Food")
        self.assertEqual(analytics.data["categories"][0]["amount"], "60.00")

    def test_equal_split_assigns_all_cents(self):
        charlie = Member.objects.create(group=self.group, name="Charlie")
        created = self.client.post("/api/expenses/", {
            "group": self.group.id, "description": "Shared", "amount": "10.00",
            "paid_by": self.alice.id, "participants": [self.alice.id, self.bob.id, charlie.id],
        }, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        from decimal import Decimal
        self.assertEqual(sum(Decimal(x) for x in created.data["shares"].values()), Decimal("10.00"))

    def test_percentage_split(self):
        response = self.client.post("/api/expenses/", {
            "group": self.group.id, "description": "Dinner", "amount": "40.00",
            "paid_by": self.alice.id, "participants": [self.alice.id, self.bob.id],
            "split_mode": "percentage", "split_values": {str(self.alice.id): "25.00", str(self.bob.id): "75.00"},
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["shares"][str(self.bob.id)], "30")

    def test_invalid_splits_and_cross_owner_writes_rejected(self):
        invalid = self.client.post("/api/expenses/", {
            "group": self.group.id, "description": "Dinner", "amount": "40.00",
            "paid_by": self.alice.id, "participants": [self.alice.id, self.bob.id],
            "split_mode": "custom", "split_values": {str(self.alice.id): "5.00", str(self.bob.id): "5.00"},
        }, format="json")
        self.assertEqual(invalid.status_code, 400)
        other_group = Group.objects.create(name="Private", owner=self.other)
        outsider = Member.objects.create(group=other_group, name="Outsider")
        for url, payload in [
            ("/api/expenses/", {"group": other_group.id, "description": "X", "amount": "10.00", "paid_by": outsider.id, "participants": [outsider.id]}),
            ("/api/settlements/", {"group": other_group.id, "paid_by": outsider.id, "paid_to": self.bob.id, "amount": "10.00"}),
        ]:
            self.assertEqual(self.client.post(url, payload, format="json").status_code, 400)
        self.assertEqual(self.client.get(f"/api/groups/{other_group.id}/analytics/").status_code, 404)

    def test_invalid_settlement_rejected(self):
        response = self.client.post("/api/settlements/", {
            "group": self.group.id, "paid_by": self.bob.id, "paid_to": self.bob.id,
            "amount": "20.00",
        }, format="json")
        self.assertEqual(response.status_code, 400)
