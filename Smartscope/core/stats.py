

# from Smartscope.core.models import AutoloaderGrid,HoleModel, HighMagModel
from Smartscope.core.models.grid import AutoloaderGrid
from Smartscope.core.models.hole import HoleModel
from Smartscope.core.models.high_mag import HighMagModel
# from Smartscope.lib.multishot import load_multishot_from_file
from .grid.run_hole import RunHole
from .grid.grid_status import GridStatus
from pydantic import BaseModel
from datetime import timedelta
from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)


class GridStats:
    ## THIS DOES NOTHING YET
    def __init__(self, grid:AutoloaderGrid):
        self.grid = grid

    

def get_hole_count(grid:AutoloaderGrid, hole_list=None):
    if hole_list is not None:
        queued = len(hole_list)
    else:
        queued = HoleModel.display.filter(grid_id=grid.grid_id,status='queued').count()
        queued_exposures = queued
    if grid.params_id.multishot_per_hole:
        mutlishot_file = Path(grid.directory,'multishot.json')
        multishot = RunHole.load_multishot_from_file(mutlishot_file)
        if multishot is not None:
            queued_exposures = queued*multishot.n_shots
    completed = HighMagModel.objects.filter(grid_id=grid.grid_id)
    num_completed = completed.count()

    holes_per_hour = 0
    last_hour = 0
    elapsed = 0
    remaining = 0
    if grid.start_time is not None:
        elapsed = grid.time_spent
        holes_per_hour = round(num_completed / (elapsed.total_seconds() / 3600), 1)
        last_hour_date_time = grid.end_time - timedelta(hours=1)
        last_hour = completed.filter(completion_time__gte=last_hour_date_time).count()
        remaining = timedelta(hours=queued_exposures/last_hour)
        
    logger.debug(f'{num_completed} completed holes, {queued} queued holes, {holes_per_hour} holes per hour, {last_hour} holes in the last hour')

    return dict(completed=num_completed, queued=queued, queued_exposures=queued_exposures, perhour=holes_per_hour, lasthour=last_hour, elapsed=str(elapsed).split('.', 2)[0], remaining=str(remaining).split('.', 2)[0])


def dashboard_stats():
    grids = AutoloaderGrid.objects.filter(status__in=[GridStatus.ABORTING,GridStatus.COMPLETED])
    num_grids=grids.count()
    age = time.time() - grids.order_by('start_time').first()
    