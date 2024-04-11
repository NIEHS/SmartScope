from ..config import PluginFactory
from pathlib import Path
from Smartscope.lib.Datatypes.base_plugin import Finder

PLUGINS_DIRECTORY = '/opt/smartscope/config/smartscope/plugins'
EXTERNAL_PLUGINS_DIRECTORY = '/opt/smartscope/external_plugins'

def test_parse_pluging_directory():
    factory = PluginFactory(plugins_directory=PLUGINS_DIRECTORY)
    factory.parse_plugins_directory()
    assert len(factory._plugins_list) == 9

def test_read_plugins_files():
    factory = PluginFactory(plugins_directory=PLUGINS_DIRECTORY)
    factory.parse_plugins_directory()
    factory.read_plugins_files()
    assert len(factory._plugins_data) == 9

def test_register_plugin():
    factory = PluginFactory(plugins_directory=PLUGINS_DIRECTORY)
    factory.parse_plugins_directory()
    factory.read_plugins_files()
    factory.register_plugin('Manual finder')
    assert len(factory._factory) == 1
    assert 'Manual finder' in factory._factory
    assert isinstance(factory._factory['Manual finder'], Finder)

def test_register_plugins():
    factory = PluginFactory(plugins_directory=PLUGINS_DIRECTORY)
    factory.parse_plugins_directory()
    factory.register_plugins()
    assert len(factory._factory) == 9

def test_get_plugins():
    factory = PluginFactory(plugins_directory=PLUGINS_DIRECTORY)
    factory.parse_plugins_directory()
    factory.register_plugins()
    plugins = factory.get_plugins()
    assert len(plugins) == 9
    assert 'Manual finder' in plugins
    assert isinstance(plugins['Manual finder'], Finder)

def test_get_plugin():
    factory = PluginFactory(plugins_directory=PLUGINS_DIRECTORY)
    factory.parse_plugins_directory()
    factory.read_plugins_files()
    factory.register_plugins()
    plugin = factory.get_plugin('Manual finder')
    assert isinstance(plugin, Finder)

