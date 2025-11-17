from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("search_benchmarking", "0002_fix_success_rate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="benchmarkresult",
            name="error_message",
            field=models.TextField(blank=True, null=True),
        ),
    ]

