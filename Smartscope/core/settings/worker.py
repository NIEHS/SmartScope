import os
from pathlib import Path
from Smartscope.lib.config import register_plugins, register_protocols
from Smartscope.core.metadata_viewer import CTFFitViewer

SMARTSCOPE_CONFIG = Path(os.getenv('APP'), 'config/smartscope/')
SMARTSCOPE_PLUGINS = SMARTSCOPE_CONFIG / 'plugins'
SMARTSCOPE_PROTOCOLS = SMARTSCOPE_CONFIG / 'protocols'

PLUGINS_FACTORY = dict()

register_plugins(SMARTSCOPE_PLUGINS, PLUGINS_FACTORY)
PLUGINS_FACTORY['CTF Viewer'] = CTFFitViewer()

PROTOCOLS_FACTORY = dict()
register_protocols(SMARTSCOPE_PROTOCOLS, PROTOCOLS_FACTORY)
