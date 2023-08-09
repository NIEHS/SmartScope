from enum import Enum
import logging
from Smartscope.lib.image.montage import Montage

logger = logging.getLogger(__name__)

class TargetClass(Enum):
    FINDER = 'Finder'
    CLASSIFIER = 'Classifier'
    SELECTOR = 'Selector'
    METADATA = 'Metadata'

def find_targets(montage: Montage, methods: list):
    logger.debug(f'Using method: {methods}')
    from Smartscope.core.settings.worker import PLUGINS_FACTORY
    for method in methods:
        method = PLUGINS_FACTORY[method]

        try:
            targets, success, additional_outputs  = method.run(montage=montage)
        except Exception as err:
            logger.exception(err)
            continue
        if success:
            logger.debug(f"{method} was successful: {success}, '+ \
                'Is Classifier: {method.target_class is TargetClass.CLASSIFIER}")
            if method.target_class is TargetClass.CLASSIFIER:
                return targets, method.name, method.name 
            else:
                return None, additional_outputs
        return [], '', None, dict()
