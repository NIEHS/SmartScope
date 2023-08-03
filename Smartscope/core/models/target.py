
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
import numpy as np

from .base_model import *
from .grid import AutoloaderGrid

from Smartscope.core.settings.worker import PLUGINS_FACTORY


class DisplayManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('finders').prefetch_related('classifiers').prefetch_related('selectors')

class TargetLabel(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=30)
    content_object = GenericForeignKey('content_type', 'object_id')
    method_name = models.CharField(max_length=50, null=True)

    class Meta:
        abstract = True
        app_label = 'API'


class Finder(TargetLabel):
    x = models.IntegerField()
    y = models.IntegerField()
    stage_x = models.FloatField()
    stage_y = models.FloatField()
    stage_z = models.FloatField(null=True)

    class Meta(BaseModel.Meta):
        db_table = 'finder'


class Classifier(TargetLabel):
    label = models.CharField(max_length=30, null=True)

    class Meta(BaseModel.Meta):
        db_table = 'classifier'


class Selector(TargetLabel):
    label = models.CharField(max_length=30, null=True)
    value = models.FloatField(null=True)

    class Meta(BaseModel.Meta):
        db_table = 'selector'

class Target(BaseModel):
    name = models.CharField(max_length=100, null=False)
    number = models.IntegerField()
    pixel_size = models.FloatField(null=True)
    shape_x = models.IntegerField(null=True)
    shape_y = models.IntegerField(null=True)
    selected = models.BooleanField(default=False)
    status = models.CharField(max_length=20, null=True, default=None)
    grid_id = models.ForeignKey(AutoloaderGrid, on_delete=models.CASCADE, to_field='grid_id')
    completion_time = models.DateTimeField(null=True)
    # Generic Relations, not fields
    finders = GenericRelation(Finder, related_query_name='target')
    classifiers = GenericRelation(Classifier, related_query_name='target')
    selectors = GenericRelation(Selector, related_query_name='target')

    display = DisplayManager()

    class Meta:
        abstract = True

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

            plugin = PLUGINS_FACTORY[selector.method_name]
            if selector.label in plugin.exclude:
                return True, selector.label

        return False, ''

    def is_good(self):
        """Looks at the classification labels and return if all the classifiers returned the square to be good for selection

        Args:
            plugins (dict): Dictionnary or sub-section from the loaded pluging.yaml.

        Returns:
            boolean: Whether the target is good for selection or not.
        """
        for label in self.classifiers.all():
            if PLUGINS_FACTORY[label.method_name].classes[label.label].value < 1:
                return False
        return True

    # def css_color(self, display_type, method):

    #     if method is None:
    #         return 'blue', 'target', ''

    #     # Must use list comprehension instead of a filter query to use the prefetched data
    #     # Reduces the amount of queries subsitantially.
    #     labels = list(getattr(self, display_type).all())
    #     label = [i for i in labels if i.method_name == method]
    #     if len(label) == 0:
    #         return 'blue', 'target', ''
    #     return PLUGINS_FACTORY[method].get_label(label[0].label)


