from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Group, Member, Expense, Settlement


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ["id", "name", "user"]


class GroupSerializer(serializers.ModelSerializer):
    members = MemberSerializer(many=True, read_only=True)
    member_names = serializers.ListField(child=serializers.CharField(max_length=100), write_only=True, required=False)

    class Meta:
        model = Group
        fields = ["id", "name", "members", "member_names", "created_at"]

    def _sync_members(self, group, names):
        cleaned = []
        seen = set()
        for name in names:
            value = name.strip()
            if value and value.lower() not in seen:
                cleaned.append(value)
                seen.add(value.lower())
        existing = {m.name.lower(): m for m in group.members.all()}
        keep_ids = []
        for name in cleaned:
            member = existing.get(name.lower())
            if member is None:
                member = Member.objects.create(group=group, name=name)
            keep_ids.append(member.id)
        for member in group.members.exclude(id__in=keep_ids):
            if member.paid_expenses.exists() or member.shared_expenses.exists() or member.settlements_paid.exists() or member.settlements_received.exists():
                continue
            member.delete()

    def create(self, validated_data):
        names = validated_data.pop("member_names", [])
        request = self.context["request"]
        group = Group.objects.create(owner=request.user, **validated_data)
        if not names:
            names = [request.user.username]
        self._sync_members(group, names)
        return group

    def update(self, instance, validated_data):
        names = validated_data.pop("member_names", None)
        instance.name = validated_data.get("name", instance.name)
        instance.save()
        if names is not None:
            self._sync_members(instance, names)
        return instance


class ExpenseSerializer(serializers.ModelSerializer):
    paid_by_name = serializers.CharField(source="paid_by.name", read_only=True)
    participant_names = serializers.SerializerMethodField()
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = Expense
        fields = ["id", "group", "group_name", "description", "amount", "paid_by", "paid_by_name", "participants", "participant_names", "created_at"]

    def get_participant_names(self, obj):
        return list(obj.participants.values_list("name", flat=True))

    def validate(self, data):
        group = data.get("group", getattr(self.instance, "group", None))
        paid_by = data.get("paid_by", getattr(self.instance, "paid_by", None))
        participants = data.get("participants", list(self.instance.participants.all()) if self.instance else [])
        amount = data.get("amount", getattr(self.instance, "amount", None))
        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount": "Expense amount must be greater than zero."})
        if paid_by and paid_by.group_id != group.id:
            raise serializers.ValidationError({"paid_by": "Payer must be a member of the group."})
        if not participants:
            raise serializers.ValidationError({"participants": "At least one participant is required."})
        if any(member.group_id != group.id for member in participants):
            raise serializers.ValidationError({"participants": "All participants must belong to the group."})
        return data


class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ["id", "group", "paid_by", "paid_to", "amount", "created_at"]
