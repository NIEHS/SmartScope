
from typing import Any, Callable, List, Union
import numpy as np
import random
import logging
from scipy.spatial.distance import cdist

from django.db.models.query import prefetch_related_objects
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from Smartscope.core.models import *
# from Smartscope.core.run_grid import load_multishot_from_file
from Smartscope.server.api.serializers import update_to_fullmeta, SvgSerializer

logger = logging.getLogger(__name__)

from django.db import models
from .models.grid import AutoloaderGrid

class Websocket_update_decorator:

    def __init__(self,
            f: Callable[[Any],
            List[Any]] = None,
            grid: Union[AutoloaderGrid, None] = None
        ):
        self.f = f
        self.grid = grid

    def __call__(self, *args, **kwargs):
        objs = self.f(*args, **kwargs)
        if not isinstance(objs, list):
            ws_objs = [objs]
        if self.grid is not None:
            websocket_update(ws_objs, self.grid.grid_id)

        return objs


def websocket_update(objs, grid_id):
    channel_layer = get_channel_layer()
    outputDict = {
        'type': 'update.metadata',
        'update': {}
    }
    logger.debug(f'Updating {objs}, sending to websocket {grid_id} group')
    outputDict['update'] = update_to_fullmeta(objs)
    async_to_sync(channel_layer.group_send)(grid_id, outputDict)


def update_target_selection(model:models.Model,objects_ids:List[str],value:str, *args, **kwargs):
    from .models.hole import HoleModel

    status = None
    value = True if value == '1' else False
    if value:
        status = 'queued'
    objs = list(model.objects.filter(pk__in=objects_ids))
    if model is HoleModel:
        bis_groups = set([obj.bis_group for obj in objs])
        squares_ids = set([obj.square_id for obj in objs])
        objs = model.objects.filter(square_id__in=squares_ids,bis_group__in=bis_groups,bis_type='center')

    with transaction.atomic():
        for obj in objs:
            obj.selected = value
            obj.status = status
            obj.save()  

def update_target_label(model:models.Model,objects_ids:List[str],value:str,method:str, *args, **kwargs):
    from .models.target_label import Classifier

    content_type = ContentType.objects.get_for_model(model)
    logger.debug('Updating Classifier objects')
    objs = Classifier.objects.filter(object_id__in=objects_ids, method_name=method)
    new_objs = set(objects_ids).difference([obj.pk for obj in objs])
    logger.debug(f'From {len(objects_ids)} ids, found {len(objs)}. Updating label to {value}')
    with transaction.atomic():
        for obj in objs: 
            obj.label = value
            obj.save()
        for obj in new_objs:
            Classifier(object_id=obj, method_name=method,content_type=content_type, label=value).save()

def update_target_status(model:models.Model,objects_ids:List[str],value:str, *args, **kwargs):
    objs = list(model.objects.filter(pk__in=objects_ids))
    with transaction.atomic():
        for obj in objs:
            obj.status = value
            obj.save()


def set_or_update_refined_finder(object_id, stage_x, stage_y, stage_z):
    from .models.target_label import Finder

    refined = Finder.objects.filter(object_id=object_id, method_name='Recentering')
    if refined:
        refined.update(stage_x=stage_x,
                        stage_y=stage_y,
                        stage_z=stage_z,)
        return
    original = Finder.objects.filter(object_id=object_id).first()
    new = Finder(
        content_type=original.content_type,
        x=original.x,
        y=original.y,
        method_name='Recentering',
        object_id=object_id,
        stage_x=stage_x,
        stage_y=stage_y,
        stage_z=stage_z,
    )
    new.save()

def viewer_only(user):
    groups = user.groups.all().values_list('name', flat=True)
    logger.debug(groups)
    if 'viewer_only' in groups:
        return True
    return False


def group_holes_for_BIS(hole_models, max_radius=4, min_group_size=1, queue_all=False, iterations=500, score_weight=2):
    if len(hole_models) == 0:
        return
    logger.debug(
        f'grouping params, max radius = {max_radius}, min group size = {min_group_size}, queue all = {queue_all}, max iterations = {iterations}, score_weight = {score_weight}')
    # Extract coordinated for the holes
    prefetch_related_objects(hole_models, 'finders')
    coords = np.array([[list(h.finders.all())[0].stage_x, list(h.finders.all())[0].stage_y] for h in hole_models])
    input_number = len(hole_models)
    # Generate distance matrix
    cd = cdist(coords, coords)
    # Fiter for distance withing max radius and get index
    filter_start = np.where(cd > max_radius, 0, 1)

    idx_list = list(range(0, input_number))

    # Find lines with the most hits as max group size
    max_group_size = np.max(np.sum(filter_start, axis=0))
    logger.debug(f'Max group size: {max_group_size}')
    best = (-1000, 0, 0, [])
    score_no_change = 0
    # Start iterations
    for iter in range(1, iterations + 1):

        groups = []
        n_holes = 0
        rd_idx_list = idx_list.copy()
        # Shuffle the index list for random looping
        filter = filter_start.copy()
        random.shuffle(rd_idx_list)
        group_size = max_group_size
        # Group from max size to min_group_size
        while group_size >= min_group_size:
            # logger.debug(f'Doing iteration: {iter}, group_size: {group_size}')
            for i in rd_idx_list:
                where = np.where(filter[i] == 1)[0]
                if len(where) >= group_size:
                    # Reseve the holes by changing the values to 2
                    filter[:, where] = 2
                    filter[where, :] = 2
                    # Add group, where i is the "center hole" and "where" are the index of the holes in the group
                    groups.append((i, where))
                    n_holes += len(where)
            group_size -= 1
        coverage = n_holes / input_number
        num_groups = len(groups)
        # score based on coverage and number of groups
        score = (coverage * 100) - (num_groups * score_weight)
        # see if iteration was better than last
        if score > best[0] or iter == 1:
            logger.debug(f'Iteration {iter}: Coverage= {coverage}, num_groups={num_groups}, score= {score}')
            best = (score, coverage, num_groups, groups)
            score_no_change = 0
        else:
            score_no_change += 1
            if score_no_change == 250:
                logger.debug('No changes for 250 iterations, stopping')
                break

    logger.info(f'Best hole grouping: Coverage= {best[1]}, num_groups={best[2]}, score= {best[0]}')

    for i, g in best[3]:
        center = hole_models[i]
        group_name = center.generate_bis_group_name()

        if queue_all:
            center.selected = True
            center.status = 'queued'

        bis = g[g != i]
        for item in bis:
            i = hole_models[item]
            i.bis_group = group_name
            i.bis_type = 'is_area'

    return hole_models


def queue_atlas(grid):
    from .models.atlas import AtlasModel

    atlas, created = AtlasModel.objects.get_or_create(
        name=f'{grid.name}_atlas',
        grid_id=grid)
    if created or atlas.status is None:
        atlas.status = 'queued'
    return atlas


@ Websocket_update_decorator
def update(instance, refresh_from_db=False, extra_fields=[], **kwargs):
    updated_fields = []
    updated_fields += extra_fields
    for key, val in kwargs.items():
        updated_fields.append(key)
        setattr(instance, key, val)
    instance = instance.save(update_fields=updated_fields)
    if refresh_from_db:
        instance.refresh_from_db()
    return instance


def add_targets(grid, parent, targets, model, finder, classifier=None, start_number=0, **extra_fields):
    from .models.square import SquareModel
    from .models.hole import HoleModel
    from .models.high_mag import HighMagModel
    from .models.target_label import Finder
    output = []
    defaut_field_dict = dict(grid_id=grid, **extra_fields)
    if model is SquareModel:
        defaut_field_dict['atlas_id'] = parent
    elif model is HoleModel:
        defaut_field_dict['square_id'] = parent
    elif model is HighMagModel:
        defaut_field_dict['hole_id'] = parent
    fields = get_fields_names(model)
    model_content_type_id = ContentType.objects.get_for_model(model)
    with transaction.atomic():
        for ind, target in enumerate(targets):
            fields_dict = defaut_field_dict.copy()
            fields_dict['number'] = ind + start_number
            for field in fields:
                val = getattr(target, field, None)
                if val is not None and field not in fields_dict.keys():
                    fields_dict[field] = val

            obj = model(**fields_dict)
            obj = obj.save()
            output.append(obj)

            finder_model = Finder(content_type=model_content_type_id, object_id=obj.pk, method_name=finder,
                                  x=target.x,
                                  y=target.y,
                                  stage_x=target.stage_x,
                                  stage_y=target.stage_y,
                                  stage_z=target.stage_z)
            finder_model.save()
            if classifier is not None:
                classifier_model = Classifier(content_type=model_content_type_id, object_id=obj.pk, method_name=classifier,
                                              label=target.quality)
                classifier_model.save()
    return output


def add_high_mag(grid, parent):
    from .models.high_mag import HighMagModel
    
    hm, created = HighMagModel.objects.get_or_create(
        number=parent.number,
        hole_id=parent,
        grid_id=grid)
    if created:
        hm = update(hm, status='started')
    return hm, created


def select_n_squares(parent, n):
    squares = np.array(parent.squaremodel_set.all().filter(selected=False, status=None).order_by('area'))
    squares = [s for s in squares if s.is_good()]
    if len(squares) == 0:
        return
    split_squares = np.array_split(squares, n)
    selection = []
    with transaction.atomic():
        for bucket in split_squares:
            if len(bucket) == 0:
                continue
            selection = random.choice(bucket)
            update(selection, selected=True, status='queued')


def select_n_holes(parent, n, is_bis=False):
    filter_fields = dict(selected=False, status=None) 
    if is_bis:
        filter_fields['bis_type'] = 'center'
    holes = list(parent.holemodel_set.filter(
        **filter_fields).order_by('dist_from_center'))

    holes = [h for h in holes if h.is_good()]

    if n <= 0:
        with transaction.atomic():
            for h in holes:
                update(h, selected=True, status='queued')
        return
    if len(holes) == 0:
        return 
    n += 1
    minimum, maximum = holes[0].dist_from_center, holes[-1].dist_from_center
    dist_range = maximum - minimum
    group_dist = dist_range / (n)
    groups = [[] for x in range(n)]
    try:
        for h in holes:
            group = min([int((h.dist_from_center - minimum) // group_dist), n - 1])
            groups[group].append(h)
    except:
        groups = np.array_split(np.array(holes), n)

    with transaction.atomic():
        for bucket in groups[:-1]:
            if len(bucket) == 0:
                continue
            selection = random.choice(bucket)
            update(selection, selected=True, status='queued')


def select_n_areas(parent, n, is_bis=False):
    filter_fields = dict(selected=False, status=None)
    if is_bis:
        filter_fields['bis_type'] = 'center'
    targets = parent.targets.filter(**filter_fields)

    if n <= 0:
        with transaction.atomic():
            for t in targets:
                if t.is_good() and not t.is_excluded()[0]:
                    update(t, selected=True, status='queued')
        return

    clusters = dict()
    for t in targets:
        if not t.is_good():
            continue
        excluded, label = t.is_excluded()
        if excluded:
            continue
        try:
            clusters[label].append(t)
        except:
            clusters[label] = [t]

    if len(clusters) > 0:
        randomized_sample = clusters if n == len(clusters) else random.sample(list(clusters), n) if n < len(clusters) else [
            random.choice(list(clusters)) for i in range(n)]
        with transaction.atomic():
            for choice in randomized_sample:
                sele = random.choice(clusters[choice])
                logger.debug(f'Selecting {sele.name} from cluster {choice}')
                update(sele, selected=True, status='queued')
    else:
        logger.info('All targets are rejected, skipping')


# def get_center_hole(instance:HoleModel):
#     if instance.bis_type == 'center':
#         return instance
#     return HoleModel.objects.get(square_id=instance.square_id, bis_group=instance.bis_group, bis_type='center')



# def update_target(data):
#     model = data.pop('type', False)
#     ids = data.pop('ids', [])
#     key = data.pop('key', False)
#     new_value = data.pop('new_value')
#     display_type = data.pop('display_type', 'classifiers')
#     method = data.pop('method', None)

#     response = dict(success=False, error=None)
#     if not key:
#         response['error'] = 'No key specified'
#         return response

#     if not key in ['label', 'selected']:
#         response['error'] = 'Wrong key choice for updating'
#         return response

#     if not model:
#         response['error'] = 'No model specified'
#         return response

#     if model == 'holes':
#         model = HoleModel

#     elif model == 'squares':
#         model = SquareModel
#     else:
#         response['error'] = 'Invalid model specified'
#         return response
#     content_type = ContentType.objects.get_for_model(model)

#     if key == 'selected':
#         new_value = True if new_value == '1' else False
#         objs = list(model.objects.filter(pk__in=ids))
#         if model is HoleModel:
#             for i, obj in enumerate(objs):
#                 if obj.bis_type == 'is_area':
#                     objs[i] = HoleModel.objects.get(square_id=obj.square_id, bis_group=obj.bis_group, bis_type='center')
#     else:
#         logger.debug('Updating Classifier objects')
#         objs = Classifier.objects.filter(object_id__in=ids, method_name=method)
#     logger.debug(f'From {len(ids)} ids, found {len(objs)}. Updating {key} to {new_value}')
#     all_found = len(ids) == len(objs)
#     with transaction.atomic():
#         if all_found:
#             for obj in objs:
#                 setattr(obj, key, new_value)
#                 obj.save()
#         else:
#             for id in ids:
#                 Classifier.objects.update_or_create(object_id=id, method_name=method,
#                                                     content_type=content_type, defaults=dict(label=new_value))
#     try:
#         instance = model.objects.get(pk=ids[0]).parent
#         response = SvgSerializer(instance=instance, display_type=display_type, method=method).data

#         response['success'] = True
#         return response
#     except Exception as err:
#         logger.exception(f"An error occured while updating the page. {err}")
#         return response

