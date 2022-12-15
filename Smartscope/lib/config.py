# from asyncio import protocols
import os
from pathlib import Path
import yaml
from Smartscope.lib.s3functions import TemporaryS3File
import logging
import importlib
import sys
from Smartscope.lib.Datatypes.base_plugin import Finder, Classifier, Selector, ImagingProtocol
from Smartscope.lib.Datatypes.base_protocol import BaseProtocol

logger = logging.getLogger(__name__)


def register_plugins(directory, factory):
    for file in directory.glob('*.yaml'):
        logger.debug(f'Registering plugin {file}')
        with open(file) as f:
            data = yaml.safe_load(f)

        if not 'pluginClass' in data.keys():
            out_class = Finder
            if 'Classifier' in data['targetClass']:
                out_class = Classifier
            if data['targetClass'] == ['Selector']:
                out_class = Selector
        else:
            split = data['pluginClass'].split('.')
            module = importlib.import_module('.'.join(split[:-1]))
            out_class = getattr(module, split[-1])

        factory[data['name']] = out_class.parse_obj(data)

def register_external_plugins(external_plugins_directory, external_plugins_list,factory):
    with open(external_plugins_list,'r') as file:
        paths = [external_plugins_directory / plugin.strip() for plugin in file.readlines()]
    
    for path in paths:
        sys.path.insert(0, str(path))
        register_plugins(path/'smartscope_plugin'/'config',factory)
        sys.path.remove(str(path))

def register_protocols(directory, factory):
    for file in directory.glob('*.yaml'):
        logger.debug(f'Registering protocol {file}')
        with open(file) as f:
            data = yaml.safe_load(f)

        factory[data['name']] = BaseProtocol.parse_obj(data)


def load_protocol(file='protocol.yaml'):
    file = Path(file)
    if file.exists():
        with open(file) as f:
            return yaml.safe_load(f)

    if eval(os.getenv('USE_AWS')):
        with TemporaryS3File([file]) as temp:
            with open(temp.temporary_files[0]) as f:
                return yaml.safe_load(f)


def save_protocol(protocol, file='protocol.yaml'):
    with open(file, 'w') as f:
        yaml.dump(protocol, f)
