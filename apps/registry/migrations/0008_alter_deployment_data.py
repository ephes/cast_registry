# Generated by Django 5.1.2 on 2024-10-17 11:13

import apps.registry.serializers
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0007_alter_deployment_processed_steps'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deployment',
            name='data',
            field=models.JSONField(encoder=apps.registry.serializers.RegistryJSONEncoder, null=True),
        ),
    ]
