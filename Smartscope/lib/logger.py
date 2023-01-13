import logging
import logging.handlers
import os
import sys

logger = logging.getLogger(__name__)


def add_log_handlers(directory: str, name: str) -> None:
    main_handler = logging.FileHandler(os.path.join(directory, name), mode='a', encoding='utf-8')
    main_handler.setFormatter(logger.parent.handlers[0].formatter)
    logging.getLogger('Smartscope').addHandler(main_handler)