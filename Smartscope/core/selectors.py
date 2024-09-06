import numpy as np
from django.db import transaction
import cv2
from typing import Optional, List

from django.contrib.contenttypes.models import ContentType
from django.db.models.query import prefetch_related_objects

from Smartscope.core.models import Selector
from Smartscope.lib.image.montage import Montage
from Smartscope.core.settings.worker import PLUGINS_FACTORY
from Smartscope.lib.image_manipulations import extract_box_from_radius
from Smartscope.lib.Finders.basic_finders import find_squares

import logging
logger = logging.getLogger(__name__)


def generate_selector(target,value:float, label:Optional[str]=None):
    return dict(content_type=ContentType.objects.get_for_model(target),
                object_id=target.pk,
                value=value,
                label=label)

def generate_selectors(targets:List, field:str, label:Optional[str]=None):
    return list(map(lambda x: generate_selector(x, value=getattr(x,field), label=label), targets))
# def generate_equal_clusters(parent, targets, n_groups, extra_fields=dict()):
#     output = list()
#     if len(targets) > 0:
#         split_targets = np.array_split(targets, n_groups)
#         for ind, bucket in enumerate(split_targets):
#             for target in bucket:
#                 extra_updates = dict()
#                 for field, attribute in extra_fields.items():
#                     extra_updates[field] = getattr(target,attribute)
#                 output.append(dict(content_type=ContentType.objects.get_for_model(target),
#                                    object_id=target.pk,
#                                    label=ind,
#                                    **extra_updates))
#     return output


def cluster_by_field(parent, field='area', **kwargs):
    targets = np.array(parent.targets.order_by(field))
    return generate_selectors(targets, field)


def prepare_selector(parent, montage):
    targets = list(parent.targets)
    prefetch_related_objects(targets, 'finders')
    logger.debug(f'Initial targets = {len(targets)}')
    if montage is None:
        montage = Montage(**parent.__dict__, working_dir=parent.grid_id.directory)
        montage.create_dirs()  
    return targets, montage


def size_selector(parent, montage=None):
    targets, montage = prepare_selector(parent, montage)
    thresh = cv2.threshold(montage.image, np.mean(montage.image), 255, cv2.THRESH_BINARY)[1]
    img = cv2.convertScaleAbs(thresh)
    for target in targets:
        finder = list(target.finders.all())[0]
        x, y = finder.x, finder.y
        radius = int(np.sqrt(target.area) // 2)
        
        extracted = img[y - radius:y + radius, x - radius:x + radius]
        target.area = np.count_nonzero(extracted) * (montage.pixel_size_micron**2)
    return generate_selectors(targets, 'area')

def gray_level_selector(parent, montage=None):
    targets, montage = prepare_selector(parent, montage)
    radius = parent.grid_id.holeType.hole_size
    apix = montage.pixel_size_micron
    if radius is None:
        radius = targets[0].radius
        apix = -1.0
    for target in targets:
        finder = list(target.finders.all())[0]
        x, y = finder.x, finder.y
        extracted = extract_box_from_radius(montage.image, x, y, radius, apix)
        target.median = np.mean(extracted)
    
    return generate_selectors(targets, 'median')

def run_selector(selector_name,selection,*args, **kwargs):
    method = PLUGINS_FACTORY.get_plugin(selector_name)
    outputs = method.run(selection, *args, **kwargs)
    with transaction.atomic():
        for obj in outputs:
            Selector(**obj, method_name=method.name).save()


def selector_wrapper(selectors, selection, *args, **kwargs):
    logger.info(f'Running selectors {selectors} on {selection}')
    for method in selectors:
        run_selector(method, selection, *args, **kwargs)


