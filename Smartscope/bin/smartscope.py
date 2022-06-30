#! /usr/bin/env python
"""Main executable for smartscope-related commands"""
import os

os.umask(int(os.getenv('DEFAULT_UMASK')))

import django
django.setup()
import sys
import logging
from Smartscope.core.main_commands import main

logger = logging.getLogger(__name__)


if __name__ == "__main__":

    args = sys.argv[1:]
    logger.debug(args)
    main(args)
