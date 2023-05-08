from typing import Dict
from django.core.cache import cache
from .session import Finder, Classifier, Selector
from django.contrib.contenttypes.models import ContentType
from Smartscope.core.settings.worker import PLUGINS_FACTORY
from Smartscope.core.metadata_viewer import CTFFitViewer
import logging

logger = logging.getLogger(__name__)


def targets_methods(instance):
    cache_key = f'{instance.pk}_targets_methods'
    if (output:=cache.get(cache_key)) is not None:
        logger.debug(f'Loading targets_method for {instance} from cache.')
        return output
    default_output = dict(finders=[], classifiers=[], selectors=[])
    if not hasattr(instance,'targets'):
        return default_output
    targets = instance.targets.values_list('pk', flat=True)
    if len(targets) == 0:
        return default_output
    contenttype = ContentType.objects.get_for_model(instance.targets.first())

    finders = list(Finder.objects.filter(content_type=contenttype, object_id__in=targets).values_list('method_name', flat=True).distinct())
    classifiers = list(Classifier.objects.filter(content_type=contenttype,
                                                 object_id__in=targets).values_list('method_name', flat=True).distinct())
    if instance.targets_prefix == 'hole' and len(classifiers) == 0:
        classifiers.append('Micrographs curation')
    selectors = list(Selector.objects.filter(content_type=contenttype, object_id__in=targets).values_list('method_name', flat=True).distinct())
    logger.debug(f'Finders: {finders}, Classifiers: {classifiers}, Selectors: {selectors}')
    output = dict(finders=[PLUGINS_FACTORY[finder] for finder in finders],
                classifiers=[PLUGINS_FACTORY[classifier] for classifier in classifiers],
                selectors=[PLUGINS_FACTORY[selector] for selector in selectors],
                metadata=[CTFFitViewer()])
    cache.set(cache_key,output,timeout=300)
    return output


def update_fields(instance, fields: Dict):
    for key, val in fields.items():
        setattr(instance, key, val)
    return instance


