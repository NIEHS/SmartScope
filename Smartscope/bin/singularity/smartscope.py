#! /usr/bin/env python
import os

# Setting up enviroment variables
# with open(f"{os.environ['SMARTSCOPE_DIR']}/conf.env", 'r') as env:
#     vars = [l.split('=') for l in env.readlines() if l[0] != "#" and l != '\n']
# for k, v in vars:
#     os.environ[k] = v.strip()
# # Setting up umask for default permissions
os.umask(int(os.getenv('DEFAULT_UMASK')))

from django.conf import settings
import django
django.setup()
import sys
import logging
from Smartscope.core.main_commands import main
from Smartscope.lib.logger import default_logger

proclog = logging.getLogger('processing')
mainlog = logging.getLogger('autoscreen')


if __name__ == "__main__":
    # default logger
    default_logger()

    args = sys.argv[1:]
    mainlog.debug(args)
    main(args)
