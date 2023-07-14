# from asyncio import protocols
import os
from typing import List
from pathlib import Path
import yaml

import logging
import importlib
import sys
from Smartscope.lib.Datatypes.base_plugin import Finder, Classifier, Selector
from Smartscope.lib.Datatypes.base_protocol import BaseProtocol

logger = logging.getLogger(__name__)


def register_plugins(directories, factory):
    for directory in directories:
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

def get_active_plugins_list(external_plugins_directory,external_plugins_list):
    with open(external_plugins_list,'r') as file:
        return [external_plugins_directory / plugin.strip() for plugin in file.readlines()]

def register_protocols(directories:List[Path], factory):
    for directory in directories:
        for file in directory.glob('*.yaml'):
            logger.debug(f'Registering protocol {file}')
            with open(file) as f:
                data = yaml.safe_load(f)
            factory[data['name']] = BaseProtocol.parse_obj(data)

def register_external_plugins(external_plugins_list,plugins_factory,protocols_factory):   
    for path in external_plugins_list:
        sys.path.insert(0, str(path))
        register_plugins([path/'smartscope_plugin'/'plugins'],plugins_factory)
        register_protocols([path/'smartscope_plugin'/'protocols'],protocols_factory)
        sys.path.remove(str(path))

def get_protocol_commands(external_plugins_list):
    from Smartscope.core.protocol_commands import protocolCommandsFactory
    for path in external_plugins_list:
        sys.path.insert(0, str(path))
        module = importlib.import_module('smartscope_plugin.protocol_commands')
        protocol_commands= getattr(module,'protocolCommandsFactory')
        sys.path.remove(str(path))
        protocolCommandsFactory.update(protocol_commands)
    return protocolCommandsFactory