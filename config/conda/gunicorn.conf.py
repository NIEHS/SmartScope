import os
import logging
import logging.handlers
import sys

bind = "127.0.0.1:9000"
wsgi_app = 'Smartscope.server.main.asgi:application'
workers = 2
reload = True
capture_output = True

proc_name = 'smartscopeGunicorn'
chdir = os.getenv('APP')
pidfile = os.path.join(os.getenv('TEMPDIR'), 'smartscopeGunicorn.pid')
worker_tmp_dir = os.getenv('TEMPDIR')
umask = int(os.getenv('DEFAULT_UMASK'))
pythonpath = os.path.join(os.getenv('CONDA_ENV'), 'bin/python')
worker_class = 'uvicorn.workers.UvicornWorker'
max_requests = 2000

GUNICORN_LOG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': sys.stdout,

        },
        'error_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'generic',
            'filename': os.path.join(os.getenv('LOGDIR'), 'gunicorn.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 90,
            'encoding': 'utf-8',
        },
        'access_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'generic',
            'filename': os.path.join(os.getenv('LOGDIR'), 'gunicornAccess.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 90,
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        '': {
            'level': os.getenv('LOGLEVEL'),
            'handlers': ['console', ],
        },
        'gunicorn.error': {
            'level': os.getenv('LOGLEVEL'),
            'handlers': ['error_file', ],
            'propagate': True,
        },
        'gunicorn.access': {
            'level': os.getenv('LOGLEVEL'),
            'handlers': ['access_file', ],
            'propagate': True
        },
    }
}


logconfig_dict = GUNICORN_LOG

# [handlers]
# keys = console, error_file, access_file

# [formatters]
# keys = generic, access


# [logger_gunicorn.error]
# level = INFO
# handlers = error_file
# propagate = 1
# qualname = gunicorn.error

# [logger_gunicorn.access]
# level = INFO
# handlers = access_file
# propagate = 0
# qualname = gunicorn.access

# [handler_console]
# class = StreamHandler


# formatter = generic
# args = (sys.stdout, )

# [handler_error_file]
# class = logging.handlers.TimedRotatingFileHandler


# formatter = generic
# args = ('/var/log/gunicorn/gunicorn-error.log', 'midnight', 1, 90, 'utf-8')

# [handler_access_file]
# class = logging.handlers.TimedRotatingFileHandler


# formatter = access
# args = ('/var/log/gunicorn/gunicorn-access.log', 'midnight', 1, 90, 'utf-8')

# [formatter_generic]
# format = %(asctime)s [% (process)d] [%(levelname)s] % (message)s
# datefmt = %Y - %m - %d % H: % M: % S
# class = logging.Formatter


# [formatter_access]
# format = %(message)s
# class = logging.Formatter


# }
