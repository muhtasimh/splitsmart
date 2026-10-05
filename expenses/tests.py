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

    def test_group_details(self):
        Expense.objects.create(group=self.group, description="Dinner", amount="60.00", paid_by=self.alice).participants.set([self.alice,self.bob])
        response = self.client.get(f"/api/groups/{self.group.id}/details/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("balances", response.data)
        self.assertIn("debts", response.data)
        self.assertIn("expenses", response.data)
