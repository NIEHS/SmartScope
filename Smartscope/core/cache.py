from django.core.cache import cache
from pathlib import Path
import logging
import json
import yaml

logger = logging.getLogger(__name__)


def save_multishot_from_cache(multishot_id, directory):
    multishot = cache.get(multishot_id)
    logger.debug(f'Getting multishot from cache at id {multishot_id}:\n{multishot}')
    with open(Path(directory,'multishot.json'),'w') as f:
        f.write(multishot)

