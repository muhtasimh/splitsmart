from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("expenses", "0002_member_and_ownership")]
    operations = [
        migrations.AddField(model_name="expense", name="split_mode", field=models.CharField(default="equal", max_length=12)),
        migrations.AddField(model_name="expense", name="shares", field=models.JSONField(default=dict, blank=True)),
        migrations.AddField(model_name="expense", name="category", field=models.CharField(default="Other", max_length=32)),
    ]
