import random
import string
from itertools import chain
import os
import json
from django.core import serializers
from Smartscope.lib.montage import Montage
import logging

logger = logging.getLogger(__name__)


def generate_unique_id(extra_inputs=[], N=30):
    if len(extra_inputs) != 0:
        base_id = ''.join(extra_inputs)
    else:
        base_id = ''
    random_id = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(N - len(base_id)))
    return ''.join([base_id, random_id]).replace('.', '_').replace(' ', '_')


# def import_session(file):
#     pass


def model_to_dict(instance, fields=None, exclude=None):
    """
    Return a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.

    ``fields`` is an optional list of field names. If provided, return only the
    named.

    ``exclude`` is an optional list of field names. If provided, exclude the
    named from the returned dict, even if they are listed in the ``fields``
    argument.
    """
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        data[f.name] = f.value_from_object(instance)
    return data


def get_fields(obj):
    return [(field.name, field.value_to_string(obj)) for field in obj._meta.fields]


def get_fields_names(model):
    return [field.name for field in model._meta.fields]


def set_shape_values(instance):
    montage = Montage(name=instance.name, working_dir=instance.grid_id.directory)
    logger.info(f'No shape found for completed image. Setting values to {montage.shape_x} X {montage.shape_y}')
    instance.shape_x = montage.shape_x
    instance.shape_y = montage.shape_y
    if instance.pixel_size is None:
        instance.pixel_size = montage.pixel_size
    instance.save()
