import logging
from Smartscope.core.settings.worker import PLUGINS_FACTORY
from Smartscope.lib.Datatypes.base_plugin import TargetClass
from Smartscope.lib.montage import Montage

logger = logging.getLogger(__name__)


def find_targets(montage: Montage, methods: list):
    logger.debug(f'Using method: {methods}')
    for method in methods:
        method = PLUGINS_FACTORY[method]

        try:
            targets, success, additional_outputs  = method.run(montage=montage)
        except Exception as err:
            logger.exception(err)
            continue
        if success:
            logger.debug(f"{method} was successful: {success}, Is Classifier: {method.target_class is TargetClass.CLASSIFIER}")

            return targets, method.name, method.name if method.target_class is TargetClass.CLASSIFIER else None, additional_outputs
