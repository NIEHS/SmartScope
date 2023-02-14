import random
import string
from itertools import chain
from typing import Callable, Union, List
from django.core.cache import cache
from django.db import models, connection, reset_queries
from Smartscope.lib.montage import Montage

import logging

logger = logging.getLogger(__name__)


class Cached_model_property:
    instance: Union[models.Model, None] = None

    def __init__(self, key_suffix:str):
        self.key_suffix= key_suffix

    @property
    def key(self):
        return '_'.join([self.instance,self.key_suffix])

    def __call__(self,func, *args, **kwargs):
        reset_queries()
        self.instance = args[0]
        if (cached_outputs := cache.get(self.key)) is not None:
            logger.debug(f'Loading {self.instance} {self.key_suffix} from cache. Required {len(connection.queries)} queries')
            return cached_outputs
        outputs = func(*args, **kwargs)
        logger.debug(f'Caching {self.instance} {self.key_suffix}. Required {len(connection.queries)} queries')
        cache.set(self.key, outputs, timeout=3600)

        return outputs

def cached_model_property(key_prefix,extra_suffix_from_function:Union[List[str],None]=None, timeout=7200):
    def outer(func):
        def inner(*args,**kwargs):
            reset_queries()
            instance = args[0]
            kwargs.update(zip(func.__code__.co_varnames, args))
            logger.debug(f'Kwargs are {kwargs}')
            key_parts = [key_prefix, instance.pk]
            if extra_suffix_from_function is not None:
                for key in extra_suffix_from_function:
                    if key in kwargs:
                        key_parts.append(kwargs[key])
            key = '_'.join(key_parts)
            if (cached_outputs := cache.get(key)) is not None:
                logger.debug(f'Loading {instance} {key_prefix} from cache. Required {len(connection.queries)} queries')
                return cached_outputs
            outputs = func(**kwargs)
            logger.debug(f'Caching {instance} {key_prefix}. Required {len(connection.queries)} queries')
            cache.set(key, outputs, timeout=timeout)
            return outputs
        return inner
    return outer
            


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
    montage.load_or_process()
    logger.info(f'No shape found for completed image. Setting values to {montage.shape_x} X {montage.shape_y}')
    instance.shape_x = montage.shape_x
    instance.shape_y = montage.shape_y
    if instance.pixel_size is None:
        instance.pixel_size = montage.pixel_size
    instance.save()
