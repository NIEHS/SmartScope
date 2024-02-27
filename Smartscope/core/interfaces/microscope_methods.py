import yaml
import logging
from Smartscope.core.settings.worker import SMARTSCOPE_CUSTOM_CONFIG
from .fakescope_interface import FakeScopeInterface
from .tfsserialem_interface import TFSSerialemInterface
from .jeolserialem_interface import JEOLSerialemInterface, JEOLadditionalSettings

logger = logging.getLogger(__name__)

def select_microscope_interface(microscope):
    additional_settings_file = SMARTSCOPE_CUSTOM_CONFIG / f'{microscope.microscope_id}.yaml'
    additional_settings = dict()
    logger.debug(f'Additional settings file: {additional_settings_file}')
    if additional_settings_file.exists():
        with open(additional_settings_file, 'r') as yaml_file:
            logger.info(f'Loading additional settings from {additional_settings_file}')
            additional_settings = yaml.safe_load(yaml_file)

    if microscope.serialem_IP == 'xxx.xxx.xxx.xxx':
        logger.info('Setting scope into test mode')
        return FakeScopeInterface, additional_settings

    if microscope.vendor == 'JEOL':
        logger.info('Using the JEOL interface')
        
        return JEOLSerialemInterface, JEOLadditionalSettings.model_validate(additional_settings)
    
    logger.info('Using the TFS interface')

    return TFSSerialemInterface, additional_settings