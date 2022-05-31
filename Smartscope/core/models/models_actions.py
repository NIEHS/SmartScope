from .session import Finder, Classifier, Selector
from django.contrib.contenttypes.models import ContentType
from Smartscope.lib.config import deep_get, load_plugins
import logging

logger = logging.getLogger(__name__)


def targets_methods(instance):
    plugins = load_plugins()
    targets = instance.base_target_query.values_list('pk', flat=True)
    contenttype = ContentType.objects.get_for_model(instance.base_target_query.first())

    finders = list(Finder.objects.filter(content_type=contenttype, object_id__in=targets).values_list('method_name', flat=True).distinct())
    classifiers = list(Classifier.objects.filter(content_type=contenttype,
                                                 object_id__in=targets).values_list('method_name', flat=True).distinct())
    if instance.targets_prefix == 'hole':
        classifiers.append('Micrographs curation')
    selectors = list(Selector.objects.filter(content_type=contenttype, object_id__in=targets).values_list('method_name', flat=True).distinct())
    logger.debug(f'Finders: {finders}, Classifiers: {classifiers}, Selectors: {selectors}')
    return dict(finders=[deep_get(plugins, finder) for finder in finders],
                classifiers=[deep_get(plugins, classifier) for classifier in classifiers],
                selectors=[deep_get(plugins, selector) for selector in selectors])
