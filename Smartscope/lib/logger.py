import logging
import logging.handlers
import os
import sys


def create_logger(name, logfile):
    # logfile = os.path.join(session.directory, 'run.out')
    FORMAT = "[%(levelname)s] %(funcName)s, %(asctime)s: %(message)s"
    logger = logging.getLogger(name)
    formatter = logging.Formatter("[%(levelname)s] %(funcName)s, %(asctime)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    # logger.setFormatter(formatter)
    fh = logging.FileHandler(logfile, mode='a', encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    # logging.basicConfig(filename=logfile, filemode='a+', format=FORMAT, datefmt="%Y-%m-%d %H:%M:%S", level=logging.DEBUG)
    logger.setLevel(os.getenv('LOGLEVEL'))
    return logger


def get_loggers():
    # if not 'autoscreen' in logging.Logger.manager.loggerDict.keys():
    #     print('No autoscreen logger found, using root logger')
    #     mainlog = logging.getLogger()
    # else:
    mainlog = logging.getLogger('autoscreen')
    # if not 'processing' in logging.Logger.manager.loggerDict.keys():
    #     print('No processing logger found, using root logger')
    #     proclog = logging.getLogger()
    # else:
    proclog = logging.getLogger('processing')
    return mainlog, proclog


def default_logger():
    FORMAT = "[%(levelname)s] %(funcName)s, %(asctime)s: %(message)s"
    rfh = logging.handlers.RotatingFileHandler(os.path.join(os.getenv('LOGDIR'), 'smartscope.log'), maxBytes=10000000, backupCount=10)
    logging.basicConfig(format=FORMAT, datefmt="%Y-%m-%d %H:%M:%S", level=logging.DEBUG, handlers=[rfh, logging.StreamHandler()])
