import os
import sys
from pathlib import Path
from Smartscope.core.config import register_plugins, register_protocols, \
    register_external_plugins, get_active_plugins_list, get_protocol_commands
# from Smartscope.core.ctf.ctf_fit_viewer import CTFFitViewer

SMARTSCOPE_CUSTOM_CONFIG = Path(os.getenv('CONFIG'))
SMARTSCOPE_DEFAULT_CONFIG = Path(__file__).parents[3] / 'config' / 'smartscope'

SMARTSCOPE_DEFAULT_PLUGINS = SMARTSCOPE_DEFAULT_CONFIG / 'plugins'
SMARTSCOPE_CUSTOM_PLUGINS = SMARTSCOPE_CUSTOM_CONFIG / 'plugins'
EXTERNAL_PLUGINS_DIRECTORY = Path(os.getenv('EXTERNAL_PLUGINS_DIRECTORY'))
sys.path.append(str(EXTERNAL_PLUGINS_DIRECTORY))
EXTERNAL_PLUGINS_LIST:list = get_active_plugins_list(
    EXTERNAL_PLUGINS_DIRECTORY,
    SMARTSCOPE_CUSTOM_CONFIG / 'external_plugins.txt'
)

SMARTSCOPE_CUSTOM_PROTOCOLS = SMARTSCOPE_CUSTOM_CONFIG / 'protocols'
SMARTSCOPE_DEFAULT_PROTOCOLS = SMARTSCOPE_DEFAULT_CONFIG / 'protocols'

##Register plugins
PLUGINS_FACTORY = dict()
register_plugins([SMARTSCOPE_DEFAULT_PLUGINS,SMARTSCOPE_CUSTOM_PLUGINS], PLUGINS_FACTORY)
PROTOCOLS_FACTORY = dict()

register_protocols([SMARTSCOPE_DEFAULT_PROTOCOLS, SMARTSCOPE_CUSTOM_PROTOCOLS], PROTOCOLS_FACTORY)
register_external_plugins( EXTERNAL_PLUGINS_LIST, plugins_factory=PLUGINS_FACTORY, protocols_factory=PROTOCOLS_FACTORY )
# PLUGINS_FACTORY['CTF Viewer'] = CTFFitViewer()

##Register available protocol commands
PROTOCOL_COMMANDS_FACTORY = get_protocol_commands(EXTERNAL_PLUGINS_LIST)

DEFAULT_PREPROCESSING_PIPELINE = [ SMARTSCOPE_CUSTOM_CONFIG / 'default_preprocessing.json', SMARTSCOPE_DEFAULT_CONFIG / 'default_preprocessing.json' ]

