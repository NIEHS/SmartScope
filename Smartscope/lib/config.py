# from asyncio import protocols
import os
from pathlib import Path
import yaml
from django.conf import settings
from Smartscope.lib.s3functions import TemporaryS3File


def load_plugins():
    with open(settings.SMARTSCOPE_PLUGINS) as f:
        return yaml.safe_load(f)


def deep_get(d, key):
    if key in d:
        return d[key]

    for k, subdict in d.items():
        if isinstance(subdict, dict):
            val = deep_get(subdict, key)
            if val:
                return val


def load_default_protocol(protocol):
    file = settings.SMARTSCOPE_PROTOCOLS
    with open(file) as f:
        protocol = yaml.safe_load(f)[protocol]
    # Sub protocol with plugins
    plugins = load_plugins()
    for k, v in protocol.items():
        for i, val in enumerate(v):
            print(val)
            pluginKey = 'selectors' if 'selector' in k.lower() else k
            protocol[k][i] = plugins[pluginKey][val]

    return protocol


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
