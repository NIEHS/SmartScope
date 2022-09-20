from typing import Dict
from .session import Finder, Classifier, Selector
from django.contrib.contenttypes.models import ContentType
# from Smartscope.lib.config import deep_get, load_plugins
from Smartscope.core.settings.worker import PLUGINS_FACTORY
from Smartscope.core.metadata_viewer import CTFFitViewer
import logging

logger = logging.getLogger(__name__)


def targets_methods(instance):
    # plugins = load_plugins()
    targets = instance.base_target_query.values_list('pk', flat=True)
    if len(targets) == 0:
        return dict(finders=[], classifiers=[], selectors=[])
    contenttype = ContentType.objects.get_for_model(instance.base_target_query.first())

    finders = list(Finder.objects.filter(content_type=contenttype, object_id__in=targets).values_list('method_name', flat=True).distinct())
    classifiers = list(Classifier.objects.filter(content_type=contenttype,
                                                 object_id__in=targets).values_list('method_name', flat=True).distinct())
    if instance.targets_prefix == 'hole' and len(classifiers) == 0:
        classifiers.append('Micrographs curation')
    selectors = list(Selector.objects.filter(content_type=contenttype, object_id__in=targets).values_list('method_name', flat=True).distinct())
    logger.debug(f'Finders: {finders}, Classifiers: {classifiers}, Selectors: {selectors}')
    return dict(finders=[PLUGINS_FACTORY[finder] for finder in finders],
                classifiers=[PLUGINS_FACTORY[classifier] for classifier in classifiers],
                selectors=[PLUGINS_FACTORY[selector] for selector in selectors],
                metadata=[CTFFitViewer()])


def update_fields(instance, fields: Dict):
    for key, val in fields.items():
        setattr(instance, key, val)
    return instance
