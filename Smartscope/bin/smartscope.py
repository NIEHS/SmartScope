#! /usr/bin/env python
"""Main executable for smartscope-related commands"""
import os
import django
import sys
import logging
logger = logging.getLogger(__name__)

if os.environ.get('mode') == 'dev':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", \
        "Smartscope.core.settings.local")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", \
        "Smartscope.core.settings.server_docker")

django.setup()
os.umask(int(os.getenv('DEFAULT_UMASK')))

from Smartscope.core.main_commands import main


if __name__ == "__main__":
    args = sys.argv[1:]
    logger.debug(args)
    main(args)
