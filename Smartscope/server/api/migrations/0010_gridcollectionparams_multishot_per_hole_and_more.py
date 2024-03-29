# Generated by Django 4.0.5 on 2023-02-22 15:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0009_selector_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='gridcollectionparams',
            name='multishot_per_hole',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='screeningsession',
            name='date',
            field=models.CharField(max_length=8),
        ),
    ]
