import os
import sys
from pathlib import Path
from Smartscope.core.config import register_protocols, \
    register_external_protocols, get_active_plugins_list, get_protocol_commands, PluginFactory
# from Smartscope.core.ctf.ctf_fit_viewer import CTFFitViewer

SMARTSCOPE_CUSTOM_CONFIG = Path(os.getenv('CONFIG'))
SMARTSCOPE_DEFAULT_CONFIG = Path(__file__).parents[3] / 'config' / 'smartscope'

SMARTSCOPE_DEFAULT_PLUGINS = SMARTSCOPE_DEFAULT_CONFIG / 'plugins'
SMARTSCOPE_CUSTOM_PLUGINS = SMARTSCOPE_CUSTOM_CONFIG / 'plugins'
EXTERNAL_PLUGINS_DIRECTORY = Path(os.getenv('EXTERNAL_PLUGINS_DIRECTORY'))
EXTERNAL_PLUGINS_LIST_FILE = SMARTSCOPE_CUSTOM_CONFIG / 'external_plugins.txt'
sys.path.append(str(EXTERNAL_PLUGINS_DIRECTORY))
EXTERNAL_PLUGINS_LIST:list = get_active_plugins_list(
    EXTERNAL_PLUGINS_DIRECTORY,
    EXTERNAL_PLUGINS_LIST_FILE
)

SMARTSCOPE_CUSTOM_PROTOCOLS = SMARTSCOPE_CUSTOM_CONFIG / 'protocols'
SMARTSCOPE_DEFAULT_PROTOCOLS = SMARTSCOPE_DEFAULT_CONFIG / 'protocols'

##Register plugins
PLUGINS_FACTORY = PluginFactory(SMARTSCOPE_DEFAULT_PLUGINS, SMARTSCOPE_CUSTOM_PLUGINS,external_plugins_list_file=EXTERNAL_PLUGINS_LIST_FILE ,external_plugins_directory=EXTERNAL_PLUGINS_DIRECTORY)
PROTOCOLS_FACTORY = dict()

register_protocols([SMARTSCOPE_DEFAULT_PROTOCOLS, SMARTSCOPE_CUSTOM_PROTOCOLS], PROTOCOLS_FACTORY)
register_external_protocols( EXTERNAL_PLUGINS_LIST, protocols_factory=PROTOCOLS_FACTORY )

##Register available protocol commands
PROTOCOL_COMMANDS_FACTORY = get_protocol_commands(EXTERNAL_PLUGINS_LIST)

DEFAULT_PREPROCESSING_PIPELINE = [ SMARTSCOPE_CUSTOM_CONFIG / 'default_preprocessing.json', SMARTSCOPE_DEFAULT_CONFIG / 'default_preprocessing.json' ]

FORCE_MDOC_TARGETING = eval(os.getenv('FORCE_MDOC_TARGETING','False'))