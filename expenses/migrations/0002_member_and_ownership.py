from django.db import migrations, models
import django.db.models.deletion


def migrate_existing(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Group = apps.get_model("expenses", "Group")
    Member = apps.get_model("expenses", "Member")
    Expense = apps.get_model("expenses", "Expense")
    Settlement = apps.get_model("expenses", "Settlement")
    through = Group._meta.get_field("legacy_members").remote_field.through

    for group in Group.objects.all():
        links = list(through.objects.filter(group_id=group.id))
        users = [User.objects.get(pk=link.user_id) for link in links]
        if users:
            group.owner_id = users[0].id
            group.save(update_fields=["owner"])
        mapping = {}
        for user in users:
            mapping[user.id] = Member.objects.create(group=group, name=user.username, user_id=user.id)

        for expense in Expense.objects.filter(group=group):
            old_payer = expense.legacy_paid_by_id
            if old_payer in mapping:
                expense.paid_by_id = mapping[old_payer].id
                expense.save(update_fields=["paid_by"])
            old_ids = list(expense.legacy_participants.values_list("id", flat=True))
            expense.participants.set([mapping[i] for i in old_ids if i in mapping])

        for settlement in Settlement.objects.filter(group=group):
            if settlement.legacy_paid_by_id in mapping and settlement.legacy_paid_to_id in mapping:
                settlement.paid_by_id = mapping[settlement.legacy_paid_by_id].id
                settlement.paid_to_id = mapping[settlement.legacy_paid_to_id].id
                settlement.save(update_fields=["paid_by", "paid_to"])


class Migration(migrations.Migration):
    dependencies = [("expenses", "0001_initial")]

    operations = [
        migrations.RenameField(model_name="group", old_name="members", new_name="legacy_members"),
        migrations.RenameField(model_name="expense", old_name="paid_by", new_name="legacy_paid_by"),
        migrations.RenameField(model_name="expense", old_name="participants", new_name="legacy_participants"),
        migrations.RenameField(model_name="settlement", old_name="paid_by", new_name="legacy_paid_by"),
        migrations.RenameField(model_name="settlement", old_name="paid_to", new_name="legacy_paid_to"),
        migrations.AddField(model_name="group", name="owner", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="owned_expense_groups", to="auth.user")),
        migrations.CreateModel(name="Member", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=100)),
            ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="expenses.group")),
            ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="expense_memberships", to="auth.user")),
        ], options={"ordering": ["name", "id"]}),
        migrations.AddField(model_name="expense", name="paid_by", field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="paid_expenses", to="expenses.member")),
        migrations.AddField(model_name="expense", name="participants", field=models.ManyToManyField(related_name="shared_expenses", to="expenses.member")),
        migrations.AddField(model_name="settlement", name="paid_by", field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="settlements_paid", to="expenses.member")),
        migrations.AddField(model_name="settlement", name="paid_to", field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="settlements_received", to="expenses.member")),
        migrations.RunPython(migrate_existing, migrations.RunPython.noop),
        migrations.RemoveField(model_name="group", name="legacy_members"),
        migrations.RemoveField(model_name="expense", name="legacy_paid_by"),
        migrations.RemoveField(model_name="expense", name="legacy_participants"),
        migrations.RemoveField(model_name="settlement", name="legacy_paid_by"),
        migrations.RemoveField(model_name="settlement", name="legacy_paid_to"),
        migrations.AlterField(model_name="expense", name="paid_by", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="paid_expenses", to="expenses.member")),
        migrations.AlterField(model_name="settlement", name="paid_by", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="settlements_paid", to="expenses.member")),
        migrations.AlterField(model_name="settlement", name="paid_to", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="settlements_received", to="expenses.member")),
    ]
