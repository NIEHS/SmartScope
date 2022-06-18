#!/usr/bin/env python

__version__ = "0.61"

import logging
import logging.config
import os
import sys

if os.getenv('LOGDIR') is not None:
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
            'file': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'formatter': 'generic',
                'filename': os.path.join(os.getenv('LOGDIR'), 'smartscope.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 90,
                'encoding': 'utf-8',
            },
        },
        'loggers': {
            # '': {
            #     'level': os.getenv('LOGLEVEL'),
            #     'handlers': ['console', ],
            # },
            __name__: {
                'level': os.getenv('LOGLEVEL'),
                'handlers': ['console', 'file', ],
                'propagate': True
            },
        }
    }
    logging.config.dictConfig(LOG)
