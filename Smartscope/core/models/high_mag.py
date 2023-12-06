from .base_model import *

from .misc_func import set_shape_values

from Smartscope.core.svg_plots import drawHighMag
from Smartscope.lib.image_manipulations import embed_image


class HighMagImageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('grid_id__session_id')

class DisplayManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('finders').prefetch_related('classifiers').prefetch_related('selectors')


from .extra_property_mixin import ExtraPropertyMixin
from .target import Target
class HighMagModel(Target, ExtraPropertyMixin):
    from .hole import HoleModel

    hm_id = models.CharField(max_length=30, primary_key=True, editable=False)
    hole_id = models.ForeignKey(
        HoleModel,
        on_delete=models.CASCADE,
        to_field='hole_id'
    )
    is_x = models.FloatField(null=True)
    is_y = models.FloatField(null=True)
    offset = models.FloatField(default=0)
    frames = models.CharField(max_length=120, null=True, default=None)
    defocus = models.FloatField(null=True)
    astig = models.FloatField(null=True)
    angast = models.FloatField(null=True)
    ctffit = models.FloatField(null=True)
    # aliases
    objects = HighMagImageManager()
    display = DisplayManager()

    class Meta(BaseModel.Meta):
        db_table = 'highmagmodel'

    @ property
    def id(self):
        return self.hm_id

    @ property
    def api_viewset_name(self):
        return 'highmag'

    @ property
    def parent(self):
        return self.hole_id

    @ parent.setter
    def set_parent(self, parent):
        self.hole_id = parent
    # endaliases
    
    def svg(self, *args, **kwargs):
        return drawHighMag(self)
    
    @property
    def power_spectrum(self):
        if self.is_aws:
            return self.ctf_img
        return embed_image(self.ctf_img)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.hm_id:
            self.name = f'{self.parent.name}_{self.number}_hm'
            self.hm_id = generate_unique_id(extra_inputs=[self.name[:20]])
        self.raw = os.path.join('raw', f'{self.name}.mrc')
        if self.status == 'completed' and (self.shape_x is None or self.pixel_size is None):
            set_shape_values(self)

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        return self

    def __str__(self):
        return self.name
