# Generated by Django 4.0.5 on 2022-06-24 14:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0002_auto_20220608_1836'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='holemodel',
            name='dist_from_center',
        ),
        migrations.AddField(
            model_name='highmagmodel',
            name='completion_time',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='gridcollectionparams',
            name='bis_max_distance',
            field=models.FloatField(default=3),
        ),
    ]