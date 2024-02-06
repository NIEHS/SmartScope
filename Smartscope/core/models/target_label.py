'''
source model with any other model through content_object
'''
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import math

from .base_model import *



class TargetLabel(BaseModel):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.CharField(max_length=30)
    content_object = GenericForeignKey('content_type', 'object_id')
    method_name = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

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

    def radius_from_origin(self, offset_x=0, offset_y=0) -> float:
        return math.sqrt((self.stage_x + offset_x) ** 2 + (self.stage_y + offset_y) ** 2)
    
    def is_position_within_stage_limits(self, stage_radius_limit:int = 975, offset_x:float=0, offset_y:float=0) -> bool:
        ##NEED TO ADD OFFSETS AND NOT HARDCODE THE LIMIT
        return self.radius_from_origin(offset_x=offset_x,offset_y=offset_y) <= stage_radius_limit


class Classifier(TargetLabel):
    label = models.CharField(max_length=30, null=True)

    class Meta(BaseModel.Meta):
        db_table = 'classifier'


class Selector(TargetLabel):
    label = models.CharField(max_length=30, null=True)
    value = models.FloatField(null=True)

    class Meta(BaseModel.Meta):
        db_table = 'selector'
            
