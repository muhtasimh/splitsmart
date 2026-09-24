from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123"
        )

    def test_valid_login_returns_token(self):
        response = self.client.post(
            "/api/token/",
            {
                "username": "testuser",
                "password": "testpassword123"
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_invalid_login_rejected(self):
        response = self.client.post(
            "/api/token/",
            {
                "username": "testuser",
                "password": "wrongpassword"
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("token", response.data)

class ExpenseValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="expenseuser",
            password="testpassword123"
        )

    def test_zero_amount_is_rejected(self):
        from .models import Group
        from .serializers import ExpenseSerializer

        group = Group.objects.create(name="Test Group")
        group.members.add(self.user)

        serializer = ExpenseSerializer(data={
            "group": group.id,
            "description": "Free Dinner",
            "amount": "0.00",
            "paid_by": self.user.id,
            "participants": [self.user.id]
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_non_group_participant_is_rejected(self):
        from .models import Group
        from .serializers import ExpenseSerializer

        outsider = User.objects.create_user(
            username="outsider",
            password="testpassword123"
        )

        group = Group.objects.create(name="Test Group")
        group.members.add(self.user)

        serializer = ExpenseSerializer(data={
            "group": group.id,
            "description": "Dinner",
            "amount": "50.00",
            "paid_by": self.user.id,
            "participants": [self.user.id, outsider.id]
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("participants", serializer.errors)

class BalanceAndDebtTests(APITestCase):
    def setUp(self):
        from .models import Group, Expense

        self.alice = User.objects.create_user(
            username="alice",
            password="testpassword123"
        )
        self.bob = User.objects.create_user(
            username="bob",
            password="testpassword123"
        )

        self.group = Group.objects.create(name="Apartment")
        self.group.members.add(self.alice, self.bob)

        self.expense = Expense.objects.create(
            group=self.group,
            description="Dinner",
            amount="60.00",
            paid_by=self.alice
        )
        self.expense.participants.add(self.alice, self.bob)

        self.client.force_authenticate(user=self.alice)

    def test_balances_are_calculated_correctly(self):
        response = self.client.get(
            f"/api/groups/{self.group.id}/balances/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        balances = {
            item["username"]: item["balance"]
            for item in response.data
        }

        self.assertEqual(balances["alice"], 30.00)
        self.assertEqual(balances["bob"], -30.00)

    def test_debt_suggestion_is_calculated_correctly(self):
        response = self.client.get(
            f"/api/groups/{self.group.id}/debts/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        debt = response.data[0]

        self.assertEqual(debt["from"], "bob")
        self.assertEqual(debt["to"], "alice")
        self.assertEqual(debt["amount"], 30.00)