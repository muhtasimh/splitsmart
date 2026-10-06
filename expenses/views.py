from decimal import Decimal
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from .models import Group, Expense, Settlement
from .serializers import UserSerializer, GroupSerializer, ExpenseSerializer, SettlementSerializer


class OwnedQuerysetMixin:
    def owner_groups(self):
        return Group.objects.filter(owner=self.request.user)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.none()
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.filter(pk=self.request.user.pk)


class GroupViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Group.objects.none()
    serializer_class = GroupSerializer
    filter_backends = [SearchFilter]
    search_fields = ["name", "members__name"]

    def get_queryset(self):
        return self.owner_groups().prefetch_related("members").distinct()

    @action(detail=True, methods=["get"])
    def details(self, request, pk=None):
        group = self.get_object()
        return Response({
            "group": GroupSerializer(group, context={"request": request}).data,
            "expenses": ExpenseSerializer(group.expenses.all(), many=True).data,
            "balances": self._balances(group),
            "debts": self._debts(group),
        })

    def _balance_map(self, group):
        balances = {member.id: Decimal("0.00") for member in group.members.all()}
        for expense in group.expenses.prefetch_related("participants"):
            participants = list(expense.participants.all())
            if not participants:
                continue
            share = expense.amount / len(participants)
            balances[expense.paid_by_id] += expense.amount
            for participant in participants:
                balances[participant.id] -= share
        for settlement in group.settlements.all():
            balances[settlement.paid_by_id] += settlement.amount
            balances[settlement.paid_to_id] -= settlement.amount
        return balances

    def _balances(self, group):
        balances = self._balance_map(group)
        return [{"member_id": m.id, "name": m.name, "balance": round(balances[m.id], 2)} for m in group.members.all()]

    def _debts(self, group):
        balances = self._balance_map(group)
        creditors, debtors = [], []
        for member in group.members.all():
            balance = balances[member.id]
            if balance > 0:
                creditors.append([member, balance])
            elif balance < 0:
                debtors.append([member, -balance])
        debts, ci, di = [], 0, 0
        while ci < len(creditors) and di < len(debtors):
            creditor, credit = creditors[ci]
            debtor, debt = debtors[di]
            payment = min(credit, debt)
            debts.append({"from": debtor.name, "to": creditor.name, "amount": round(payment, 2)})
            creditors[ci][1] -= payment
            debtors[di][1] -= payment
            if creditors[ci][1] == 0: ci += 1
            if debtors[di][1] == 0: di += 1
        return debts

    @action(detail=False, methods=["get"], url_path="my-balance")
    def my_balance(self, request):
        total = Decimal("0.00")
        for group in self.get_queryset():
            balances = self._balance_map(group)
            # Each group is private to its owner, so the owner's balance is
            # represented by the member whose name matches the signed-in username.
            # Prefer that deterministic mapping over a stale Member.user link left
            # behind by older data.
            member = group.members.filter(name__iexact=request.user.username).first()
            if member is not None:
                if member.user_id != request.user.id:
                    member.user = request.user
                    member.save(update_fields=["user"])
                total += balances.get(member.id, Decimal("0.00"))
        return Response({
            "balance": round(total, 2),
            "owed": round(max(total, Decimal("0.00")), 2),
            "owe": round(max(-total, Decimal("0.00")), 2),
        })

    @action(detail=True, methods=["get"])
    def balances(self, request, pk=None):
        return Response(self._balances(self.get_object()))

    @action(detail=True, methods=["get"])
    def debts(self, request, pk=None):
        return Response(self._debts(self.get_object()))


class ExpenseViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Expense.objects.none()
    serializer_class = ExpenseSerializer
    filter_backends = [SearchFilter]
    search_fields = ["description", "group__name", "paid_by__name", "participants__name"]

    def get_queryset(self):
        return Expense.objects.filter(group__owner=self.request.user).select_related("group", "paid_by").prefetch_related("participants").distinct()


class SettlementViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Settlement.objects.none()
    serializer_class = SettlementSerializer

    def get_queryset(self):
        return Settlement.objects.filter(group__owner=self.request.user)


def dashboard(request):
    return render(request, "expenses/index.html")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    username = str(request.data.get("username", "")).strip()
    password = str(request.data.get("password", ""))
    confirm_password = str(request.data.get("confirm_password", ""))
    if not username or not password:
        return Response({"detail": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)
    if password != confirm_password:
        return Response({"detail": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username__iexact=username).exists():
        return Response({"detail": "That username is already taken."}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(username=username, password=password)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "username": user.username}, status=status.HTTP_201_CREATED)
