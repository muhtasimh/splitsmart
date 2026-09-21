from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Group, Expense, Settlement


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "members", "created_at"]


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            "id",
            "group",
            "description",
            "amount",
            "paid_by",
            "participants",
            "created_at",
        ]

    def validate(self, data):
        group = data.get("group")
        paid_by = data.get("paid_by")
        participants = data.get("participants", [])
        amount = data.get("amount")

        if amount is not None and amount <= 0:
            raise serializers.ValidationError(
                {"amount": "Expense amount must be greater than zero."}
            )

        if paid_by not in group.members.all():
            raise serializers.ValidationError(
                {"paid_by": "Payer must be a member of the group."}
            )

        if not participants:
            raise serializers.ValidationError(
                {"participants": "At least one participant is required."}
            )

        for participant in participants:
            if participant not in group.members.all():
                raise serializers.ValidationError(
                    {"participants": "All participants must belong to the group."}
                )

        return data


class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = [
            "id",
            "group",
            "paid_by",
            "paid_to",
            "amount",
            "created_at",
        ]

    def validate(self, data):
        group = data.get("group")
        paid_by = data.get("paid_by")
        paid_to = data.get("paid_to")
        amount = data.get("amount")

        if amount is not None and amount <= 0:
            raise serializers.ValidationError(
                {"amount": "Settlement amount must be greater than zero."}
            )

        if paid_by == paid_to:
            raise serializers.ValidationError(
                "A user cannot settle a debt with themselves."
            )

        if paid_by not in group.members.all() or paid_to not in group.members.all():
            raise serializers.ValidationError(
                "Both users must be members of the group."
            )

        return data