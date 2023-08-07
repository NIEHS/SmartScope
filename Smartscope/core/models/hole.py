from .base_model import *


from .misc_func import set_shape_values
from Smartscope.core.svg_plots import drawMediumMag



class HoleImageManager(models.Manager):
    use_for_related_fields = True

    def __init__(self):
        super().__init__()

    def get_queryset(self):
        return super().get_queryset().prefetch_related('grid_id__session_id').prefetch_related('highmagmodel_set')

class HoleDisplayManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('finders').prefetch_related('classifiers').prefetch_related('selectors').prefetch_related('highmagmodel_set')


from .target import Target
from .extra_property_mixin import ExtraPropertyMixin
class HoleModel(Target, ExtraPropertyMixin):
    from .square import SquareModel

    hole_id = models.CharField(max_length=30, primary_key=True, editable=False)
    radius = models.IntegerField()  # Can be removed and area can be put in the target class
    area = models.FloatField()
    square_id = models.ForeignKey(
        SquareModel,
        on_delete=models.CASCADE,
        to_field='square_id'
    )

    bis_group = models.CharField(max_length=30, null=True)
    bis_type = models.CharField(max_length=30, null=True)

    objects = HoleImageManager()
    just_holes = models.Manager()
    display = HoleDisplayManager()

    def generate_bis_group_name(self):
        if self.bis_group is None:
            self.bis_group = f'{self.parent.number}_{self.number}'
            self.bis_type = 'center'
        return self.bis_group

    @ property
    def alias_name(self):
        return f'Target {self.number}'

    @property
    def prefix(self):
        return 'Hole'

    @ property
    def targets(self):
        from .high_mag import HighMagModel
        if self.bis_group is None:
            return HighMagModel.objects.filter(hole_id=self.hole_id)

        holes_in_group = HoleModel.objects.filter(square_id=self.square_id,bis_group=self.bis_group).values_list('hole_id', flat=True)
        return HighMagModel.display.filter(hole_id__in=holes_in_group)

    @ property
    def targets_prefix(self):
        return 'high_mag'

    @ property
    def api_viewset_name(self):
        return 'holes'

    @ property
    def id(self):
        return self.hole_id

    # @cached_model_property(key_prefix='svg', extra_suffix_from_function=['method'], timeout=3600)
    def svg(self, display_type, method):
        holes = list(self.targets)
        if self.shape_x is None:  # There was an error in previous version where shape wasn't set.
            set_shape_values(self)
        radius = 0.5
        if self.grid_id.holeType.hole_size is not None:
            radius = self.grid_id.holeType.hole_size/2 
        
        sq = drawMediumMag(self, holes, display_type, method, radius=radius)
        return sq

    @ property
    def bisgroup_acquired(self):
        if self.bis_group is not None:
            status_set = set(list(self.targets.values_list('status', flat=True)))
        else:
            if self.high_mag is None:
                return False
            status_set = set([self.high_mag.status])
        logger.debug(f'Status set = {status_set}')
        if list(status_set) in [['acquired'], ['processed']] or len(status_set) > 1:
            return True
        elif status_set == set(['completed']):
            self.status = 'completed'
            self.save()
            return True
        return False

    @ property
    def parent(self):
        return self.square_id

    @ parent.setter
    def set_parent(self, parent):
        self.square_id = parent

    @ property
    def stage_z(self):
        return self.parent.stage_z

    @ property
    def high_mag(self):
        return self.highmagmodel_set.first()

    class Meta(BaseModel.Meta):
        # TODO
        # unique_together = ('name', 'square_id')
        db_table = 'holemodel'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.hole_id:
            self.name = f'{self.parent.name}_hole{self.number}'
            self.hole_id = generate_unique_id(extra_inputs=[self.name[:20]])
        self.raw = os.path.join('raw', f'{self.name}.mrc')

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return self.name


