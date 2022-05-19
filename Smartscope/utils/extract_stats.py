from cv2 import textureFlattening
from Smartscope.core.models import *
import logging
import numpy as np
import pandas as pd
from Smartscope.core.db_manipulations import get_hole_count

FORMAT = "[%(levelname)s] %(funcName)s, %(asctime)s: %(message)s"
logging.basicConfig(format=FORMAT, datefmt="%Y-%m-%d %H:%M:%S", level=logging.DEBUG)
proclog = logging.getLogger('processing')
mainlog = logging.getLogger('autoscreen')


def get_grids_stats_screening():

    all_grids = list(AutoloaderGrid.objects.all())
    df = pd.DataFrame(columns=['gridName', 'date', 'squareCount', 'holeCount', 'timeSpent'])
    for grid in all_grids:
        if grid.collection_mode == 'screening' and grid.start_time is not None:
            df = df.append(dict(
                grid_id=grid.grid_id,
                date=grid.start_time.date(),
                holeCount=grid.count_acquired_holes,
                squareCount=grid.count_acquired_squares,
                timeSpent=grid.time_spent.seconds / 60,
                isBis=grid.params_id.bis_max_distance > 0
            ), ignore_index=True
            )

    return df


def get_grids_stats_datacollection(grid_ids: list = []):
    def f(x):
        return x.total_seconds() / 60

    if len(grid_ids) == 0:
        all_grids = list(AutoloaderGrid.objects.all())
    else:
        all_grids = list(AutoloaderGrid.objects.filter(grid_id__in=grid_ids))
    data_collection = [g for g in all_grids if g.collection_mode == 'collection']
    df = pd.DataFrame(columns=['gridName', 'date', 'completed', 'perhour', 'timeSpent', 'timeTo50', 'collectionType'])
    for grid in data_collection:
        if grid.count_acquired_holes < 50:
            print('Skipping', grid)
            continue
        count_stats = get_hole_count(grid)
        if count_stats['perhour'] is not None:
            hole_times = list(map(f, np.sort(np.array(grid.holemodel_set.filter(
                status='completed').values_list('completion_time', flat=True)) - grid.start_time)))
            if len(hole_times) == 0 or max(hole_times) > 10000 or min(hole_times) > 1000 or hole_times[50] > 120:
                print('Skipping', grid)
                continue

            count_stats['timeTo50'] = hole_times[50]
            count_stats['grid_id'] = grid.grid_id
            count_stats['date'] = grid.start_time.date()
            count_stats['timeSpent'] = grid.time_spent.total_seconds() / 60
            if max(hole_times) < 1080:
                count_stats['collectionType'] = 'overnight'

            else:
                count_stats['collectionType'] = 'weekend'
            df = df.append(count_stats, ignore_index=True)

    return df

# def getStatsObject(itemlist):
#     return stats(np.min(itemlist), np.max(itemlist), np.mean(itemlist), np.std(itemlist))
