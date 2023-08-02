from .base_model import *


class GridCollectionParamsManager(models.Manager):
    def get_by_natural_key(self, microscope_id, name):
        return self.get(microscope_id=microscope_id, name=name)


class GridCollectionParams(BaseModel):
    params_id = models.CharField(max_length=30, primary_key=True, editable=False)
    atlas_x = models.IntegerField(default=3)
    atlas_y = models.IntegerField(default=3)
    square_x = models.IntegerField(default=1)
    square_y = models.IntegerField(default=1)
    squares_num = models.IntegerField(default=3)
    holes_per_square = models.IntegerField(default=3)  # If -1 means all
    bis_max_distance = models.FloatField(default=3)  # 0 means not BIS
    min_bis_group_size = models.IntegerField(default=1)
    afis = models.BooleanField(default=False, verbose_name='AFIS')
    target_defocus_min = models.FloatField(default=-2)
    target_defocus_max = models.FloatField(default=-2)
    step_defocus = models.FloatField(default=0)  # 0 deactivates step defocus
    drift_crit = models.FloatField(default=-1)
    tilt_angle = models.FloatField(default=0)
    save_frames = models.BooleanField(default=True)
    force_process_from_average = models.BooleanField(default=False)
    offset_targeting = models.BooleanField(default=True)
    offset_distance = models.FloatField(default=-1)
    zeroloss_delay = models.IntegerField(default=-1)
    hardwaredark_delay = models.IntegerField(default=-1,verbose_name='Hardware Dark Delay')
    multishot_per_hole = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        db_table = 'gridcollectionparams'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.params_id:
            self.params_id = generate_unique_id()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return f'Atlas:{self.atlas_x}X{self.atlas_y} Sq:{self.squares_num} H:{self.holes_per_square} BIS:{self.bis_max_distance} Def:{self.target_defocus_min},{self.target_defocus_max},{self.step_defocus}'
