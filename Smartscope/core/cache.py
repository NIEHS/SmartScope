from django.core.cache import cache
from pathlib import Path
import logging
import json
import yaml

logger = logging.getLogger(__name__)

def save_json_from_cache(item_id, directory, file_root_name):
    cached_item = cache.get(item_id)
    logger.debug(f'Getting {file_root_name} from cache at id {item_id}:\n{cached_item}')
    with open(Path(directory,f'{file_root_name}.json'),'w') as f:
        f.write(cached_item)