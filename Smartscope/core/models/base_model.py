
from datetime import datetime
import os
from django.contrib.auth.models import User, Group
from django.db import models
from django.conf import settings
from django.core.cache import cache
from Smartscope.lib.Datatypes.models import generate_unique_id

import logging
logger = logging.getLogger(__name__)


class BaseModel(models.Model):
    """
    For future abstraction.
    """
    class Meta:
        abstract = True
        app_label = 'API'