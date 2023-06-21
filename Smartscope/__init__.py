#!/usr/bin/env python

import logging
import logging.config
from pathlib import Path
import os
import sys

version_file = Path(__file__).parents[1].resolve() / 'VERSION'
__version__ = version_file.read_text()

LOGLEVEL = os.getenv('LOGLEVEL') if os.getenv('LOGLEVEL') is not None else 'DEBUG'

LOG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(name)s:%(lineno)s - %(levelname)8s]   %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': sys.stdout,
        },
    },
    'loggers': {
        __name__: {
            'level': LOGLEVEL,
            'handlers': ['console', ],
        },
    }
}

if os.getenv('LOGDIR') is not None:
    LOG['handlers']['file'] = {
        'class': 'logging.handlers.TimedRotatingFileHandler',
        'formatter': 'generic',
        'filename': os.path.join(os.getenv('LOGDIR'), 'smartscope.log'),
        'when': 'midnight',
        'interval': 1,
        'backupCount': 90,
        'encoding': 'utf-8',
    }
    LOG['loggers'][__name__]['handlers'].append('file')

logging.config.dictConfig(LOG)


# by tiezheng
import pymysql
pymysql.install_as_MySQLdb()
