import logging
import logging.config
import os
import sys

LOG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(name)s:%(lineno)s %(funcName)5s - %(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': sys.stdout,
        },
        'server_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'generic',
            'filename': os.path.join(os.getenv('LOGDIR'), 'smartscopeServer.log'),
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
            'handlers': ['console', 'server_file', ],
            'propagate': True
        },
    }
}
logging.config.dictConfig(LOG)
