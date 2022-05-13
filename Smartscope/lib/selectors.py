from Smartscope.lib.config import load_plugins
from Smartscope.server.models import *
from django.contrib.contenttypes.models import ContentType
from Smartscope.lib.montage import *
import Smartscope.lib.logger
import numpy as np
from django.db import transaction
import cv2
from Smartscope.lib.image_manipulations import save_image, to_8bits, auto_contrast
Smartscope.lib.logger.default_logger()

proclog = logging.getLogger('processing')
mainlog = logging.getLogger('autoscreen')


def generate_equal_clusters(parent, targets, n_groups):
    output = list()
    if len(targets) > 0:
        split_targets = np.array_split(targets, n_groups)
        for ind, bucket in enumerate(split_targets):
            for target in bucket:
                output.append(dict(content_type=ContentType.objects.get_for_model(parent),
                                   object_id=target.pk,
                                   defaults=dict(label=ind)))
    return output


def cluster_by_field(parent, n_groups, field='area'):
    plugins = load_plugins()

    targets = np.array(parent.targets.order_by(field))
    output = []
    mainlog.debug(plugins)
    # targets = [t for t in targets if t.is_good(plugins=plugins)]

    return generate_equal_clusters(parent, targets, n_groups)


def gray_level_selector(parent, n_groups, save=True, montage=None):
    targets = list(parent.targets)
    mainlog.debug(f'Initial targets = {len(targets)}')
    if montage is None:
        montage = Montage(**parent.__dict__, working_dir=parent.grid_id.directory)
        montage.create_dirs()
    if save:
        img = cv2.bilateralFilter(auto_contrast(montage.raw_montage.copy()), 30, 75, 75)
    for target in targets:
        x, y = target.finders[0].x, target.finders[0].y

        target.median = np.mean(img[y - target.radius:y + target.radius, x - target.radius:x + target.radius])
        if save:
            cv2.circle(img, (x, y), target.radius, target.median, 10)

    if save:
        save_image(img, 'gray_level_selector', extension='png', destination=parent.directory, resize_to=1024)

    targets.sort(key=lambda x: x.median)
    mainlog.debug([t.median for t in targets])
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
        proclog.debug(import_cmd)
        proclog.debug(f"kwargs = {method['kwargs']}")
        exec(import_cmd)
        try:
            outputs = locals()[method['method']](selection, *args, *method['args'], **method['kwargs'], **kwargs)
            with transaction.atomic():
                for obj in outputs:
                    obj['method_name'] = method['name']
                    Selector.objects.update_or_create(**obj)
                    # obj.save()
        except Exception as err:
            proclog.exception(err)
