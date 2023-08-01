import numpy as np
from django.db import transaction
import cv2

from django.contrib.contenttypes.models import ContentType
from django.db.models.query import prefetch_related_objects

from Smartscope.core.models import Selector
from Smartscope.lib.image.montage import Montage
from Smartscope.core.settings.worker import PLUGINS_FACTORY
from Smartscope.lib.image_manipulations import save_image, to_8bits, auto_contrast

import logging
logger = logging.getLogger(__name__)


def generate_equal_clusters(parent, targets, n_groups):
    output = list()
    if len(targets) > 0:
        split_targets = np.array_split(targets, n_groups)
        for ind, bucket in enumerate(split_targets):
            for target in bucket:
                output.append(dict(content_type=ContentType.objects.get_for_model(target),
                                   object_id=target.pk,
                                   label=ind))
    return output


def cluster_by_field(parent, n_groups, field='area', **kwargs):

    targets = np.array(parent.targets.order_by(field))
    return generate_equal_clusters(parent, targets, n_groups)


def gray_level_selector(parent, n_groups, save=True, montage=None):
    targets = list(parent.targets)
    prefetch_related_objects(targets, 'finders')
    logger.debug(f'Initial targets = {len(targets)}')
    if montage is None:
        montage = Montage(**parent.__dict__, working_dir=parent.grid_id.directory)
        montage.create_dirs()
    if save:
        img = cv2.bilateralFilter(auto_contrast(montage.image.copy()), 30, 75, 75)
    for target in targets:
        finder = list(target.finders.all())[0]
        x, y = finder.x, finder.y
        target.median = np.mean(img[y - target.radius:y + target.radius, x - target.radius:x + target.radius])
        if save:
            cv2.circle(img, (x, y), target.radius, target.median, 10)

    if save:
        save_image(img, 'gray_level_selector', extension='png', destination=parent.directory, resize_to=1024)

    targets.sort(key=lambda x: x.median)
    return generate_equal_clusters(parent, targets, n_groups)


def selector_wrapper(selectors, selection, *args, **kwargs):
    logger.info(f'Running selectors {selectors} on {selection}')
    for method in selectors:
        method = PLUGINS_FACTORY[method]

        outputs = method.run(selection, *args, **kwargs)
        with transaction.atomic():
            for obj in outputs:
                Selector(**obj, method_name=method.name).save()
