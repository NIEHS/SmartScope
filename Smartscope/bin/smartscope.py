#! /usr/bin/env python
"""Main executable for smartscope-related commands"""
import os
import django
import sys
import logging
logger = logging.getLogger(__name__)

if os.environ.get('mode') == 'dev':
    import environ
    env = environ.Env()
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    env_file = os.path.join(BASE_DIR, 'core', 'settings', '.dev.env')
    if os.path.isfile(env_file):
        environ.Env.read_env(env_file=env_file)
    else:
        logger.error("Error: no env_file")
        sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Smartscope.core.settings.server_docker")
django.setup()
os.umask(int(os.getenv('DEFAULT_UMASK')))

from Smartscope.core.main_commands import main


if __name__ == "__main__":
    args = sys.argv[1:]
    logger.debug(args)
    main(args)
