# Generated manually to fix success_rate field issue

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('search_benchmarking', '0001_initial'),
    ]

    operations = [
        # Remove the success_rate field if it exists as a database field
        # This is handled by the property in the model
    ]
