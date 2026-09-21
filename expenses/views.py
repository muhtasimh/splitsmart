from django.contrib.auth.models import User
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from .models import Group, Expense, Settlement
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    UserSerializer,
    GroupSerializer,
    ExpenseSerializer,
    SettlementSerializer,
)

from decimal import Decimal
from rest_framework.decorators import action
from rest_framework.response import Response

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    @action(detail=True, methods=["get"])
    def balances(self, request, pk=None):
        group = self.get_object()

        balances = {
            member.id: Decimal("0.00")
            for member in group.members.all()
        }

        for expense in group.expenses.all():
            participants = list(expense.participants.all())

            if not participants:
                continue

            share = expense.amount / len(participants)

            balances[expense.paid_by.id] += expense.amount

            for participant in participants:
                balances[participant.id] -= share

        for settlement in group.settlements.all():
            balances[settlement.paid_by.id] += settlement.amount
            balances[settlement.paid_to.id] -= settlement.amount

        result = []

        for member in group.members.all():
            result.append({
                "user_id": member.id,
                "username": member.username,
                "balance": round(balances[member.id], 2),
            })

        return Response(result)

    @action(detail=True, methods=["get"])
    def debts(self, request, pk=None):
        group = self.get_object()

        balances = {
            member.id: Decimal("0.00")
            for member in group.members.all()
        }

        for expense in group.expenses.all():
            participants = list(expense.participants.all())

            if not participants:
                continue

            share = expense.amount / len(participants)
            balances[expense.paid_by.id] += expense.amount

            for participant in participants:
                balances[participant.id] -= share

        for settlement in group.settlements.all():
            balances[settlement.paid_by.id] += settlement.amount
            balances[settlement.paid_to.id] -= settlement.amount

        creditors = []
        debtors = []

        for member in group.members.all():
            balance = balances[member.id]

            if balance > 0:
                creditors.append([member, balance])
            elif balance < 0:
                debtors.append([member, -balance])

        debts = []
        creditor_index = 0
        debtor_index = 0

        while creditor_index < len(creditors) and debtor_index < len(debtors):
            creditor, credit = creditors[creditor_index]
            debtor, debt = debtors[debtor_index]

            payment = min(credit, debt)

            debts.append({
                "from": debtor.username,
                "to": creditor.username,
                "amount": round(payment, 2),
            })

            creditors[creditor_index][1] -= payment
            debtors[debtor_index][1] -= payment

            if creditors[creditor_index][1] == 0:
                creditor_index += 1

            if debtors[debtor_index][1] == 0:
                debtor_index += 1

        return Response(debts)

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["group", "paid_by"]
    search_fields = ["description"]


class SettlementViewSet(viewsets.ModelViewSet):
    queryset = Settlement.objects.all()
    serializer_class = SettlementSerializer

def dashboard(request):
    return render(request, "expenses/index.html")

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)