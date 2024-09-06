
from django.contrib.contenttypes.fields import GenericRelation
import numpy as np

from .base_model import *
from Smartscope.core.settings.worker import PLUGINS_FACTORY


class DisplayManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()\
            .prefetch_related('finders')\
            .prefetch_related('classifiers')\
            .prefetch_related('selectors')

class Target(BaseModel):
    from .grid import AutoloaderGrid
    from .target_label import Finder, Classifier, Selector
    
    name = models.CharField(max_length=100, null=False)
    number = models.IntegerField()
    pixel_size = models.FloatField(null=True)
    shape_x = models.IntegerField(null=True)
    shape_y = models.IntegerField(null=True)
    selected = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        null=True,
        default=None
    )
    grid_id = models.ForeignKey(
        AutoloaderGrid,
        on_delete=models.CASCADE,
        to_field='grid_id'
    )
    completion_time = models.DateTimeField(null=True)
    # Generic Relations, not fields
    finders = GenericRelation(Finder, related_query_name='target')
    classifiers = GenericRelation(Classifier, related_query_name='target')
    selectors = GenericRelation(Selector, related_query_name='target')

    display = DisplayManager()

    class Meta:
        abstract = True

    @property
    def prefix(self):
        raise NotImplementedError('Prefix must be implemented in the subclass')
    
    @property
    def prefix_lower(self):
        return self.prefix.lower()

    @property
    def group(self):
        return self.grid_id.session_id.group

    @property
    def stage_coords(self) -> np.ndarray:
        finder = self.finders.first()
        return np.array([finder.stage_x, finder.stage_y])
    
    @property
    def coords(self) -> np.ndarray:
        finder = self.finders.first()
        return np.array([finder.x, finder.y])

    def is_excluded(self):
        for selector in self.selectors.all():
            plugin = PLUGINS_FACTORY.get_plugin(selector.method_name)
            if selector.label in plugin.exclude:
                return True, selector.label
        return False, ''

    def is_good(self):
        """
        Looks at the classification labels and 
        return if all the classifiers returned 
        the square to be good for selection

        Args:
            plugins (dict): Dictionnary or sub-section from the loaded pluging.yaml.
        Returns:
            boolean: Whether the target is good for selection or not.
        """
        for label in self.classifiers.all():
            if PLUGINS_FACTORY[label.method_name].classes[label.label].value < 1:
                return False
        return True

    def is_position_within_stage_limits(self, stage_radius_limit:int = 975, offset_x:float=0, offset_y:float=0) -> bool:
        return self.finders.first().is_position_within_stage_limits(stage_radius_limit, offset_x, offset_y)


