
from django.db import models

class BaseModel(models.Model):
    """
    For future abstraction.
    """
    class Meta:
        abstract = True
        app_label = 'API'