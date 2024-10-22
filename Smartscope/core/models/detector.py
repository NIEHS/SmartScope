
from .base_model import *

DETECTOR_CHOICES = (
    ('K2', 'Gatan K2'),
    ('K3', 'Gatan K3'),
    ('Ceta', 'FEI Ceta'),
    ('Falcon3', 'TFS Falcon 3'),
    ('Falcon4', 'TFS Falcon 4')
)

class DetectorManager(models.Manager):
    def get_by_natural_key(self, microscope_id, name):
        return self.get(microscope_id=microscope_id, name=name)


class Detector(BaseModel):
    from .microscope import Microscope

    name = models.CharField(max_length=100)
    microscope_id = models.ForeignKey(
        Microscope,
        on_delete=models.CASCADE,
        to_field='microscope_id'
    )
    detector_model = models.CharField(
        max_length=30,
        choices=DETECTOR_CHOICES
    )
    atlas_mag = models.IntegerField(default=210)
    atlas_max_tiles_X = models.IntegerField(default=6)
    atlas_max_tiles_Y = models.IntegerField(default=6)
    spot_size = models.IntegerField(default=None, null=True)
    c2_perc = models.FloatField(default=100)
    atlas_c2_aperture = models.IntegerField(default=70, help_text='Size of the aperture in microns to use during the atlas procedure. Should be set to 0 on JEOL to remove the aperture.')
    atlas_to_search_offset_x = models.FloatField(
        default=0,
        help_text='X stage offset between the atlas and ' + \
            'Search mag. Similar to the Shift to Marker offset.'
    )
    atlas_to_search_offset_y = models.FloatField(
        default=0,
        help_text='Y stage offset between the atlas and ' + \
            'Search mag. Similar to the Shift to Marker offset.'
    )
    frame_align_cmd = models.CharField(max_length=30, default='alignframes')
    gain_rot = models.IntegerField(default=0, null=True)
    gain_flip = models.BooleanField(default=True)
    energy_filter = models.BooleanField(default=False)
    frames_windows_directory = models.CharField(
        max_length=200,
        default='movies',
        blank=True,
        help_text='Location of the frames from the perspective of SerialEM. ' + \
            'This values will use the SetDirectory command. Leave this field empty for Falcon detectors.'
    )
    # frame_directory is path used in container
    # that should be mapped to real dir at server
    # for example: /mnt/krios_Raid_X/smartscope
    frames_directory = models.CharField(
        max_length=200,
        default='/mnt/scope/movies/',
        help_text='Location of the frames directory from SmartScope that point ' + \
            'to the same location as frames_windows_directory.'
    )
    deprecated = models.BooleanField(default=False, help_text='This detector is no longer in use. This will effectively hide the detector from the user interface while still keeping the data in the database for historical session.')

    objects = DetectorManager()

    class Meta(BaseModel.Meta):
        db_table = 'detector'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'{self.microscope_id} - {self.name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def natural_key(self):
        return (self.microscope_id, self.name)
