from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from .base_model import BaseModel
# from .grid import AutoloaderGrid

class Tag(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        abstract = True

    def __str__(self):
        return self.name


class UserGroupTag(Tag):
    user_id = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    group_name = models.ForeignKey(Group, to_field='name',on_delete=models.CASCADE)
    
    class Meta(BaseModel.Meta):
        abstract = True

    def __str__(self):
        return f"{self.name} - {self.group_name} - {self.user_id}"



class TagGrid(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    grid_id = models.ForeignKey('AutoloaderGrid', on_delete=models.CASCADE)


class SampleTag(UserGroupTag):
    pass


class ProjectTag(UserGroupTag):
    pass


class SampleTypeTag(Tag):
    pass