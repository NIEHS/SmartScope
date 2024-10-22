# Generated by Django 4.2.2 on 2024-10-22 13:51

from django.db import migrations, models


def create_models(apps, schema_editor):
    meshSize = apps.get_model('API', 'MeshSize')
    holeType = apps.get_model('API', 'HoleType')

    meshSize.objects.create(name="50Hex", square_size=50, bar_width=11, pitch=61)
    holeType.objects.create(name="HexAUFoil", hole_size=0.29, hole_spacing=0.31)


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0023_gridcollectionparams_beam_centering_delay_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='detector',
            name='deprecated',
            field=models.BooleanField(default=False, help_text='This detector is no longer in use. This will effectively hide the detector from the user interface while still keeping the data in the database for historical session.'),
        ),
        migrations.RunPython(create_models),
    ]



