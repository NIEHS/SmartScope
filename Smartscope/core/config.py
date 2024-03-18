# from asyncio import protocols
import os
from typing import List, Dict, Optional, Union
from pathlib import Path
import yaml

import logging
import importlib
import sys
from Smartscope.lib.Datatypes.base_plugin import BaseFeatureAnalyzer, Finder, Classifier, Selector
from Smartscope.lib.Datatypes.base_protocol import BaseProtocol

logger = logging.getLogger(__name__)




def register_plugin(data):
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
    return out_class

def register_plugins(directories, factory):
    for directory in directories:
        for file in directory.glob('*.yaml'):
            logger.debug(f'Registering plugin {file}')
            with open(file) as f:
                data = yaml.safe_load(f)

            out_class = register_plugin(data)

            factory[data['name']] = out_class.model_validate(data)

def get_active_plugins_list(external_plugins_directory,external_plugins_list):
    with open(external_plugins_list,'r') as file:
        return [external_plugins_directory / plugin.strip() for plugin in file.readlines()]

def register_protocols(directories:List[Path], factory):
    for directory in directories:
        for file in directory.glob('*.yaml'):
            logger.debug(f'Registering protocol {file}')
            with open(file) as f:
                data = yaml.safe_load(f)
            factory[data['name']] = BaseProtocol.model_validate(data)

def register_external_plugins(external_plugins_list,plugins_factory,protocols_factory):   
    for path in external_plugins_list:
        register_plugins([path/'smartscope_plugin'/'plugins'],plugins_factory)
        register_protocols([path/'smartscope_plugin'/'protocols'],protocols_factory)

def get_protocol_commands(external_plugins_list):
    from Smartscope.core.protocol_commands import protocolCommandsFactory
    for path in external_plugins_list:
        module = importlib.import_module(path.name +'.smartscope_plugin.protocol_commands')
        protocol_commands= getattr(module,'protocolCommandsFactory')
        protocolCommandsFactory.update(protocol_commands)
    return protocolCommandsFactory

class PluginDoesnNotExistError(Exception):

    def __init__(self, plugin, plugins:Optional[Dict]= None) -> None:
        if plugins is not None:
            message = f'Plugin \'{plugin}\' does not exist. Available plugins are: {list(plugins.keys())}'
        super().__init__(message)

class PluginFactory:
    _plugins_directory: Path
    _external_plugins_directory: Optional[Path] = None
    _external_plugins_list_file: Optional[Path] = None
    _plugins_list: List[Path] = []
    _plugins_data: Dict[str, Dict] = {}
    _factory: Dict[str, BaseFeatureAnalyzer] = {}

    def __init__(self, plugins_directory: Union[str,Path], external_plugins_list_file: Optional[Union[str,Path]]=None, external_plugins_directory: Optional[Union[str,Path]]=None) -> None:
        self._plugins_directory = Path(plugins_directory)
        if all([external_plugins_list_file is not None, external_plugins_directory is not None]):
            self._external_plugins_list_file = Path(external_plugins_list_file)
            self._external_plugins_directory = Path(external_plugins_directory)
        # self.parse_plugins_directory()
        # self.read_plugins_files()
        # self.register_plugins()

    def parse_plugins_directory(self) -> None:
        self._plugins_list += list(self._plugins_directory.glob('*.yaml'))
        if self._external_plugins_directory is not None:
            pass

    def read_plugins_files(self) -> None:
        for file in self._plugins_list:
            logger.debug(f'Reading plugin {file}')
            with open(file) as f:
                data = yaml.safe_load(f)
            self._plugins_data[data['name']] = data

    def register_plugin(self, name:str) -> None:
        data = self._plugins_data[name]
        out_class = register_plugin(data)
        logger.debug(f'Registering plugin {name}')
        self._factory[name] = out_class.model_validate(data)        

    def register_plugins(self):
        for name in self._plugins_data.keys():
            self.register_plugin(name)

    def get_plugin(self, name) -> BaseFeatureAnalyzer:
        if (plugin := self._factory.get(name)) is not None:
            logger.debug(f'Getting plugin {name}')
            return plugin
        if self._plugins_list.get(name) is not None:
            logger.debug(f'Plugin {name} not registered, registering it now.')
            return self._register_plugin(name)
        raise PluginDoesnNotExistError(name, self._factory)

    def get_plugins(self):
        return self._factory
    
    def reload_plugins(self):
        self._plugins_list = []
        self._plugins_data = {}
        self._factory = {}
        self.parse_plugins_directory(PLUGINS_DIRECTORY)