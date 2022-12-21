import os
from pathlib import Path
from Smartscope.core.config import register_plugins, register_protocols, register_external_plugins, get_active_plugins_list, get_protocol_commands
from Smartscope.core.metadata_viewer import CTFFitViewer

SMARTSCOPE_CONFIG = Path(os.getenv('APP'), 'config/smartscope/')
SMARTSCOPE_PLUGINS = SMARTSCOPE_CONFIG / 'plugins'
EXTERNAL_PLUGINS_DIRECTORY = Path(os.getenv('APP'), 'external_plugins')
EXTERNAL_PLUGINS_LIST:list = get_active_plugins_list(EXTERNAL_PLUGINS_DIRECTORY, SMARTSCOPE_PLUGINS / 'external_plugins.txt')
SMARTSCOPE_PROTOCOLS = SMARTSCOPE_CONFIG / 'protocols'

##Register plugins
PLUGINS_FACTORY = dict()
register_plugins(SMARTSCOPE_PLUGINS, PLUGINS_FACTORY)
register_external_plugins( EXTERNAL_PLUGINS_LIST, PLUGINS_FACTORY )
PLUGINS_FACTORY['CTF Viewer'] = CTFFitViewer()



##Register available protocol commands
PROTOCOL_COMMANDS_FACTORY = get_protocol_commands(EXTERNAL_PLUGINS_LIST)

PROTOCOLS_FACTORY = dict()
register_protocols(SMARTSCOPE_PROTOCOLS, PROTOCOLS_FACTORY)

