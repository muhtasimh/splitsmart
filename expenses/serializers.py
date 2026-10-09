from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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
    current_member_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Group
        fields = ["id", "name", "members", "member_names", "current_member_name", "created_at"]

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

    def _link_current_member(self, group, member_name):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return
        if not member_name:
            group.members.filter(user=request.user).update(user=None)
            return
        member = group.members.filter(name__iexact=member_name.strip()).first()
        if member is None:
            raise serializers.ValidationError({"current_member_name": "Choose one of the group's members as yourself."})
        group.members.filter(user=request.user).exclude(pk=member.pk).update(user=None)
        if member.user_id != request.user.id:
            member.user = request.user
            member.save(update_fields=["user"])

    def create(self, validated_data):
        names = validated_data.pop("member_names", [])
        current_member_supplied = "current_member_name" in validated_data
        current_member_name = validated_data.pop("current_member_name", "")
        request = self.context["request"]
        group = Group.objects.create(owner=request.user, **validated_data)
        self._sync_members(group, names)
        self._link_current_member(group, current_member_name)
        return group

    def update(self, instance, validated_data):
        names = validated_data.pop("member_names", None)
        current_member_supplied = "current_member_name" in validated_data
        current_member_name = validated_data.pop("current_member_name", "")
        instance.name = validated_data.get("name", instance.name)
        instance.save()
        if names is not None:
            self._sync_members(instance, names)
        if current_member_supplied:
            self._link_current_member(instance, current_member_name)
        return instance


class ExpenseSerializer(serializers.ModelSerializer):
    paid_by_name = serializers.CharField(source="paid_by.name", read_only=True)
    participant_names = serializers.SerializerMethodField()
    group_name = serializers.CharField(source="group.name", read_only=True)
    split_values = serializers.DictField(child=serializers.DecimalField(max_digits=12, decimal_places=2), write_only=True, required=False)

    class Meta:
        model = Expense
        fields = ["id", "group", "group_name", "description", "amount", "paid_by",
                  "paid_by_name", "participants", "participant_names", "split_mode",
                  "split_values", "shares", "category", "created_at"]
        read_only_fields = ["shares"]

    def get_participant_names(self, obj):
        return list(obj.participants.values_list("name", flat=True))

    def validate(self, data):
        group = data.get("group", getattr(self.instance, "group", None))
        paid_by = data.get("paid_by", getattr(self.instance, "paid_by", None))
        participants = data.get("participants", list(self.instance.participants.all()) if self.instance else [])
        amount = data.get("amount", getattr(self.instance, "amount", None))
        mode = data.get("split_mode", getattr(self.instance, "split_mode", "equal"))
        values = data.get("split_values", None)
        if group is None or group.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError({"group": "Invalid group."})
        if amount is None or amount <= 0:
            raise serializers.ValidationError({"amount": "Expense amount must be greater than zero."})
        if paid_by is None or paid_by.group_id != group.id:
            raise serializers.ValidationError({"paid_by": "Payer must be a member of the group."})
        if not participants:
            raise serializers.ValidationError({"participants": "At least one participant is required."})
        if any(member.group_id != group.id for member in participants):
            raise serializers.ValidationError({"participants": "All participants must belong to the group."})
        if mode not in ("equal", "percentage", "custom"):
            raise serializers.ValidationError({"split_mode": "Invalid split mode."})
        ids = [str(m.id) for m in sorted(participants, key=lambda m: m.id)]
        cents = int((amount * 100).to_integral_value())
        if mode == "equal":
            base, remainder = divmod(cents, len(ids))
            shares = {member_id: str(Decimal(base + (i < remainder)) / 100) for i, member_id in enumerate(ids)}
        else:
            if values is None and self.instance and not any(k in data for k in ("amount", "participants", "split_mode")) and mode == self.instance.split_mode:
                shares = self.instance.shares
            else:
                if values is None or set(values) != set(ids):
                    raise serializers.ValidationError({"split_values": "Provide a value for every participant."})
                if any(value < 0 for value in values.values()):
                    raise serializers.ValidationError({"split_values": "Values cannot be negative."})
                if mode == "percentage":
                    if sum(values.values()) != Decimal("100.00"):
                        raise serializers.ValidationError({"split_values": "Percentages must total 100."})
                    raw = {k: (amount * values[k] / 100) for k in ids}
                    allocated = {k: int((raw[k] * 100).to_integral_value(rounding=ROUND_HALF_UP)) for k in ids}
                    difference = cents - sum(allocated.values())
                    allocated[ids[0]] += difference
                    shares = {k: str(Decimal(allocated[k]) / 100) for k in ids}
                else:
                    if sum(values.values()) != amount:
                        raise serializers.ValidationError({"split_values": "Custom amounts must equal the expense total."})
                    shares = {k: str(values[k]) for k in ids}
        data["shares"] = shares
        data.pop("split_values", None)
        return data


class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ["id", "group", "paid_by", "paid_to", "amount", "created_at"]

    def validate(self, data):
        group = data.get("group", getattr(self.instance, "group", None))
        payer = data.get("paid_by", getattr(self.instance, "paid_by", None))
        receiver = data.get("paid_to", getattr(self.instance, "paid_to", None))
        amount = data.get("amount", getattr(self.instance, "amount", None))
        if group is None or group.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError({"group": "Invalid group."})
        if not payer or payer.group_id != group.id or not receiver or receiver.group_id != group.id:
            raise serializers.ValidationError("Both members must belong to the group.")
        if payer.pk == receiver.pk:
            raise serializers.ValidationError("A member cannot pay themselves.")
        if amount is None or amount <= 0:
            raise serializers.ValidationError({"amount": "Settlement amount must be positive."})
        return data
