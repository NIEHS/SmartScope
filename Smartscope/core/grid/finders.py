import logging
from Smartscope.lib.image.montage import Montage
from Smartscope.lib.Datatypes.base_plugin import TargetClass
from Smartscope.core.settings.worker import PLUGINS_FACTORY, FORCE_MDOC_TARGETING

logger = logging.getLogger(__name__)

def find_targets(montage: Montage, methods: list):
    logger.debug(f'Using method: {methods}')
    
    for method in methods:
        method = PLUGINS_FACTORY.get_plugin(method)

        try:
            targets, success, additional_outputs  = method.run(montage=montage, force_mdoc=FORCE_MDOC_TARGETING)
        except Exception as err:
            logger.exception(err)
            success = False
            continue
        if success:
            logger.debug(f"{method} was successful: {success}, '+ \
                'Is Classifier: {method.target_class is TargetClass.CLASSIFIER}")
            if method.target_class is TargetClass.CLASSIFIER:
                return targets, method.name, method.name, additional_outputs
            else:
                return targets, method.name, None, additional_outputs
    return [], '', None, dict()
