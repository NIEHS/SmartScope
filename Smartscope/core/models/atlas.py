from .base_model import *
from .extra_property_mixin import ExtraPropertyMixin
from .grid import AutoloaderGrid


from Smartscope.core.svg_plots import drawAtlas

class AtlasModel(BaseModel, ExtraPropertyMixin):
    atlas_id = models.CharField(max_length=30, primary_key=True, editable=False)
    name = models.CharField(max_length=100, null=False)
    pixel_size = models.FloatField(null=True)
    binning_factor = models.FloatField(null=True)
    shape_x = models.IntegerField(null=True)
    shape_y = models.IntegerField(null=True)
    stage_z = models.FloatField(null=True)
    grid_id = models.ForeignKey(AutoloaderGrid, on_delete=models.CASCADE, to_field='grid_id')
    status = models.CharField(max_length=20, null=True, default=None)
    completion_time = models.DateTimeField(null=True)

    # aliases

    @property
    def group(self):
        return self.grid_id.session_id.group

    @ property
    def alias_name(self):
        return 'Atlas'

    @property
    def prefix_lower(self):
        return self.prefix.lower()

    @property
    def prefix(self):
        return 'Atlas'

    @ property
    def api_viewset_name(self):
        return 'atlas'

    @ property
    def targets_prefix(self):
        return 'square'

    @ property
    def id(self):
        return self.atlas_id

    @ property
    def parent(self):
        return self.grid_id

    @ parent.setter
    def set_parent(self, parent):
        self.grid_id = parent

    @ property
    def targets(self):
        return self.squaremodel_set.all()

    # @cached_model_property(key_prefix='svg', extra_suffix_from_function=['method'], timeout=3600)
    def svg(self, display_type, method):
        from .square import SquareModel
        
        targets = list(SquareModel.display.filter(atlas_id=self.atlas_id))
        return drawAtlas(self,targets , display_type, method)

    class Meta(BaseModel.Meta):
        unique_together = ('grid_id', 'name')
        db_table = 'atlasmodel'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.atlas_id:
            self.name = f'{self.grid_id.name}_atlas'
            self.atlas_id = generate_unique_id(extra_inputs=[self.name[:20]])
        self.raw = os.path.join('raw', f'{self.name}.mrc')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return self.name
