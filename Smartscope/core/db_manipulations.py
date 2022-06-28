
from typing import Any, Callable, List, Union
from Smartscope.lib.config import load_plugins
from Smartscope.core.models import *
from scipy.spatial.distance import cdist
import numpy as np
import random
import logging
from django.db.models.query import prefetch_related_objects
from django.db import transaction
from datetime import timedelta
from Smartscope.server.api.serializers import update_to_fullmeta, SvgSerializer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.contenttypes.models import ContentType


logger = logging.getLogger(__name__)


class Websocket_update_decorator:

    def __init__(self, f: Callable[[Any], List[Any]] = None, grid: Union[AutoloaderGrid, None] = None):
        self.f = f
        self.grid = grid

    def __call__(self, *args, **kwargs):
        objs = outputs = self.f(*args, **kwargs)
        if not isinstance(outputs, list):
            objs = [objs]
        if self.grid is not None:
            websocket_update(objs, self.grid.grid_id)

        return outputs


def websocket_update(objs, grid_id):

    channel_layer = get_channel_layer()

    outputDict = {'type': 'update.metadata',
                  'update': {}}

    logger.debug(f'Updating {objs}, sending to websocket {grid_id} group')
    outputDict['update'] = update_to_fullmeta(objs)
    async_to_sync(channel_layer.group_send)(grid_id, outputDict)


def update_target(data):
    model = data.pop('type', False)
    ids = data.pop('ids', [])
    key = data.pop('key', False)
    new_value = data.pop('new_value')
    display_type = data.pop('display_type', 'classifiers')
    method = data.pop('method', None)

    response = dict(success=False, error=None)
    if not key:
        response['error'] = 'No key specified'
        return response

    if not key in ['label', 'selected']:
        response['error'] = 'Wrong key choice for updating'
        return response

    if not model:
        response['error'] = 'No model specified'
        return response

    if model == 'holes':
        model = HoleModel

    elif model == 'squares':
        model = SquareModel
    else:
        response['error'] = 'Invalid model specified'
        return response
    content_type = ContentType.objects.get_for_model(model)
    if method is None:
        objs = list(model.objects.filter(pk__in=ids))
        if key == 'selected' and model is HoleModel:
            for i, obj in enumerate(objs):
                if obj.bis_type == 'is_area':
                    objs[i] = HoleModel.objects.get(square_id=obj.square_id, bis_group=obj.bis_group, bis_type='center')

    else:
        logger.debug('Updating Classifier objects')
        objs = Classifier.objects.filter(object_id__in=ids, method_name=method)
    logger.debug(f'From {len(ids)} ids, found {len(objs)}. Updating {key} to {new_value}')
    all_found = len(ids) == len(objs)
    # return_objs = []
    with transaction.atomic():
        if all_found:
            for obj in objs:
                setattr(obj, key, new_value)
                obj.save()
        else:
            for id in ids:
                Classifier.objects.update_or_create(object_id=id, method_name=method,
                                                    content_type=content_type, defaults=dict(label=new_value))
    try:
        instance = model.objects.get(pk=ids[0]).parent
        response = SvgSerializer(instance=instance, display_type=display_type, method=None).data

        response['success'] = True
        return response
    except Exception as err:
        logger.exception("An error occured while updating the page.")
        return response


def get_hole_count(grid, hole_list=None):
    plugins = load_plugins()
    protocol = load_protocol(os.path.join(grid.directory, 'protocol.yaml'))
    if hole_list is not None:
        all_holes = hole_list
    else:
        all_holes = list(HoleModel.display.filter(grid_id=grid.grid_id))
    completed = [hole for hole in all_holes if hole.status == 'completed']
    if len(completed) == 0:
        return dict(completed=0, queued=0, perhour=0, last_hour=0)
    num_completed = len(completed)
    queued = 0
    all_queued = [hole for hole in all_holes if hole.status == 'queued']
    for hole in all_queued:
        if hole.bis_group is not None:
            queued += len([h for h in all_holes if h.bis_group == hole.bis_group and h.is_good(plugins=plugins)
                          and not h.is_excluded(protocol, 'hole')[0]])
        else:
            queued += 1
    holes_per_hour = None
    last_hour = None
    if grid.start_time is not None:

        holes_per_hour = round(num_completed / (grid.time_spent.total_seconds() / 3600), 1)

        last_hour_date_time = grid.end_time - timedelta(hours=1)
        last_hour = len([h for h in completed if h.completion_time >= last_hour_date_time])
    logger.debug(f'{num_completed} completed holes, {queued} queued holes, {holes_per_hour} holes per hour, {last_hour} holes in the last hour')
    return dict(completed=num_completed, queued=queued, perhour=holes_per_hour, lasthour=last_hour)


def viewer_only(user):
    groups = user.groups.all().values_list('name', flat=True)
    logger.debug(groups)
    if 'viewer_only' in groups:
        return True
    return False


def group_holes_for_BIS(hole_models, max_radius=4, min_group_size=1, queue_all=False, iterations=500, score_weight=2):
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

        bis = g[g != i]
        for item in bis:
            i = hole_models[item]
            i.bis_group = group_name
            i.bis_type = 'is_area'

    return hole_models


def queue_atlas(grid):
    atlas, created = AtlasModel.objects.get_or_create(
        name=f'{grid.name}_atlas',
        grid_id=grid)
    # print('Atlas newly created? ', created, ' Status: ', atlas.status)
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
    # close_old_connections()
    instance = instance.save(update_fields=updated_fields)
    if refresh_from_db:
        instance.refresh_from_db()
    return instance


def add_targets(grid, parent, targets, model, finder, classifier=None, start_number=0, **extra_fields):
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
    # all_objects = model.objects.all().filter(**defaut_field_dict)
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
    hm, created = HighMagModel.objects.get_or_create(
        number=parent.number,
        hole_id=parent,
        grid_id=grid)
    if created:
        hm = update(hm, status='started')
    return hm, created


def select_n_squares(parent, n):
    squares = np.array(parent.squaremodel_set.all().filter(selected=False, status=None).order_by('area'))
    plugins = load_plugins()['squareFinders']
    logger.debug(plugins)
    squares = [s for s in squares if s.is_good(plugins=plugins)]
    if len(squares) > 0:
        split_squares = np.array_split(squares, n)
        selection = []
        with transaction.atomic():
            for bucket in split_squares:
                if len(bucket) > 0:
                    selection = random.choice(bucket)
                    update(selection, selected=True, extra_fields=['status'])


def select_n_holes(parent, n, is_bis=False):
    plugins = load_plugins()['holeFinders']
    filter_fields = dict(selected=False, status=None)  # , class_num__lt=2
    if is_bis:
        filter_fields['bis_type'] = 'center'
    holes = list(parent.holemodel_set.filter(
        **filter_fields).order_by('dist_from_center'))
    # if len(holes) == 0:
    #     # To still select holes when they are all predicted to be bad. Because we're not sure the classifier is working well yet (added v.0.44)
    #     logger.info('No holes new selected, overlooking prediction classes')
    #     filter_fields.pop('class_num__lt')
    #     logger.debug(filter_fields)
    #     holes = list(parent.holemodel_set.filter(
    #         **filter_fields).order_by('dist_from_center'))

    holes = [h for h in holes if h.is_good(plugins=plugins)]

    if n <= 0:
        with transaction.atomic():
            for h in holes:
                update(h, selected=True, extra_fields=['status'])
        return
    if len(holes) > 0:
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
        # print(groups)
        with transaction.atomic():
            for bucket in groups[:-1]:
                if len(bucket) > 0:
                    selection = random.choice(bucket)
                    update(selection, selected=True, extra_fields=['status'])


def select_n_areas(parent, n, is_bis=False):
    plugins = load_plugins()
    protocol = load_protocol(os.path.join(parent.grid_id.directory, 'protocol.yaml'))
    filter_fields = dict(selected=False, status=None)
    if is_bis:
        filter_fields['bis_type'] = 'center'
    targets = parent.base_target_query.filter(**filter_fields)

    if n <= 0:
        with transaction.atomic():
            for t in targets:
                if t.is_good(plugins=plugins) and not t.is_excluded(protocol, parent.targets_prefix)[0]:
                    update(t, selected=True, extra_fields=['status'])
        return

    clusters = dict()
    for t in targets:
        if t.is_good(plugins=plugins):
            excluded, label = t.is_excluded(protocol, parent.targets_prefix)
            if not excluded:
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
                update(sele, selected=True, extra_fields=['status'])
    else:
        logger.info('All targets are rejected, skipping')
    # targets_filtered = [t for t in targets if t.is_good(plugins=plugins) and not t.is_excluded(protocol, parent.targets_prefix)]

    # logger.debug(f"{len(targets)}, {len(targets_filtered)}")
