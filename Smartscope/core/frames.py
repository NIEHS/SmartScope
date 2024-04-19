import yaml
import re
import logging
from Smartscope.core.models import AutoloaderGrid
from Smartscope.core.settings.worker import SMARTSCOPE_CUSTOM_CONFIG

logger = logging.getLogger(__name__)


def get_frames_prefix(grid:AutoloaderGrid):
    detector = grid.parent.detector_id
    custom_paths = SMARTSCOPE_CUSTOM_CONFIG / 'custom_paths.yaml'
    if not custom_paths.exists():
        logger.debug(f'No custom paths file found at {custom_paths}')
        return ''
    file = yaml.safe_load(custom_paths.read_text())
    key = f'detector_id_{detector.pk}'
    paths = file.get(key, None)
    if paths is None:
        logger.debug(f'No key {key} file found at {custom_paths}')
        return ''
    return paths.get('frames_prefix', '')


def parse_frames_prefix(prefix:str, grid:AutoloaderGrid):
    pattern = r'.*(\{\{.*\}\})'
    matches = re.findall(pattern, prefix)
    for match in matches:
        clean_match = match.replace('{{', '').replace('}}', '')
        split = clean_match.split('.')
        x = grid
        for s in split:
            x = getattr(x, s)
        logger.debug(f'Parsed {match} to {x}')
        prefix = prefix.replace(match,x)
    return prefix