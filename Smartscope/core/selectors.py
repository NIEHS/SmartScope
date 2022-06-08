from Smartscope.lib.config import load_plugins
from Smartscope.core.models import Selector
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import prefetch_related_objects
from Smartscope.lib.montage import Montage
import numpy as np
from django.db import transaction
import cv2
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
                                   defaults=dict(label=ind)))
    return output


def cluster_by_field(parent, n_groups, field='area', **kwargs):
    plugins = load_plugins()

    targets = np.array(parent.targets.order_by(field))
    output = []
    logger.debug(plugins)
    # targets = [t for t in targets if t.is_good(plugins=plugins)]

    return generate_equal_clusters(parent, targets, n_groups)


def gray_level_selector(parent, n_groups, save=True, montage=None):
    targets = list(parent.targets)
    prefetch_related_objects(targets, 'finders')
    logger.debug(f'Initial targets = {len(targets)}')
    if montage is None:
        montage = Montage(**parent.__dict__, working_dir=parent.grid_id.directory)
        montage.create_dirs()
    if save:
        img = cv2.bilateralFilter(auto_contrast(montage.raw_montage.copy()), 30, 75, 75)
    for target in targets:
        finder = list(target.finders.all())[0]
        x, y = finder.x, finder.y
        # logger.debug(f'X:{type(x)},Y:{type(y)},Radius:{type(target.radius)}')
        target.median = np.mean(img[y - target.radius:y + target.radius, x - target.radius:x + target.radius])
        if save:
            cv2.circle(img, (x, y), target.radius, target.median, 10)

    if save:
        save_image(img, 'gray_level_selector', extension='png', destination=parent.directory, resize_to=1024)

    targets.sort(key=lambda x: x.median)
    # logger.debug([t.median for t in targets])
    # split_targets = np.array_split(np.array(targets), n_groups)
    # output = list()
    return generate_equal_clusters(parent, targets, n_groups)


def selector_wrapper(selectors, selection, *args, **kwargs):

    for method in selectors:
        if not 'args' in method.keys():
            method['args'] = []
        if not 'kwargs' in method.keys():
            method['kwargs'] = dict()

        import_cmd = f"from {method['package']} import {method['method']}"
        logger.debug(import_cmd)
        logger.debug(f"kwargs = {method['kwargs']}")
        exec(import_cmd)
        try:
            outputs = locals()[method['method']](selection, *args, *method['args'], **method['kwargs'], **kwargs)
            with transaction.atomic():
                for obj in outputs:
                    # obj['method_name'] = method['name']
                    Selector(**obj, method_name=method['name']).save()
                    # obj.save()
        except Exception as err:
            logger.exception(err)
