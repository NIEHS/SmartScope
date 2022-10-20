#!/usr/bin/env python

__version__ = "0.8b2"

import logging
import logging.config
import os
import sys

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
        # '': {
        #     'level': LOGLEVEL,
        #     'handlers': ['console', ],
        # },
        __name__: {
            'level': LOGLEVEL,
            'handlers': ['console', ],
            # 'propagate': True
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

# print(LOG)

logging.config.dictConfig(LOG)
