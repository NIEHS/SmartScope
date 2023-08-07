'''
source model with any other model through content_object
'''
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from .base_model import *



class TargetLabel(BaseModel):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
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
