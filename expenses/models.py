from django.db import models
from django.contrib.auth.models import User


class Group(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_expense_groups", null=True, blank=True)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="expense_memberships", null=True, blank=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="expenses")
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="paid_expenses")
    participants = models.ManyToManyField(Member, related_name="shared_expenses")
    split_mode = models.CharField(max_length=12, default="equal")
    shares = models.JSONField(default=dict, blank=True)
    category = models.CharField(max_length=32, default="Other")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.description


class Settlement(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="settlements")
    paid_by = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="settlements_paid")
    paid_to = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="settlements_received")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
