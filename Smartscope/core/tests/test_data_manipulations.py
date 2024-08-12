from functools import partial
import logging
import Smartscope.bin.smartscope

from Smartscope.core.data_manipulations import get_target_methods,filter_targets, prepare_filtered_set, select_random_areas, count_filtered, filter_targets, filter_out_of_range, randomized_choice, choose_get_index
from Smartscope.core.models import SquareModel, HoleModel, AtlasModel

logger = logging.getLogger(__name__)

def test_get_target_methods():
    targets = HoleModel.objects.filter(square_id='testgrid_1_square8rcOwL7B01hSK')
    methods = get_target_methods(targets, 'selectors')
    assert len(methods) == 1

def test_filter_targets():
    parent = SquareModel.objects.get(pk='testgrid_1_square8rcOwL7B01hSK')
    targets= parent.targets.all()
    filtered = filter_targets(parent, targets)
    assert len(set(filtered)) == 6
    assert len(filtered) == len(targets)

def test_filter_out_of_range():
    logger.info('Testing filter out of range')
    parent = AtlasModel.objects.get(pk='testgrid_1_atlasDXdHqPR3RhyJm9')
    targets = parent.targets.all()
    filter_oor_partial = partial(filter_out_of_range, stage_radius_limit=200, offset_x=0, offset_y=0)
    filtered = list(map(filter_oor_partial, targets))
    logger.debug(f'Number of targers: {len(filtered)}. Number of targets out of range: {count_filtered(filtered)}')

    assert len(filtered) == len(targets)
    assert set(filtered) == {0,1}

def test_filter_targets_and_out_of_range():
    logger.info('Testing filter targets and out of range')
    parent = AtlasModel.objects.get(pk='testgrid_1_atlasDXdHqPR3RhyJm9')
    targets = parent.targets.all()
    filtered = filter_targets(parent, targets, stage_radius_limit=100, offset_x=0, offset_y=0)
    filter_oor_partial = partial(filter_out_of_range, stage_radius_limit=100, offset_x=0, offset_y=0)
    filtered_oor= list(map(filter_oor_partial, targets))
    for item, item_oor in zip(filtered, filtered_oor):
        if item_oor == 0:
            assert item == 0
        # assert item >= item_oor

def test_prepare_filtered_set():
    filters = [0,0,1,0,1,1,2]
    filtered_set = prepare_filtered_set(filters)
    assert len(filtered_set) == 2
    assert 0 not in filtered_set   

def test_randomized_choice():
    filtered_set = {1,2,3,4,5}
    choices = randomized_choice(filtered_set.copy(), 3)
    assert len(choices) == 3
    assert len(set(choices)) == len(choices)

    choices = randomized_choice(filtered_set.copy(), 12)
    print(f'Choices are {choices}')
    assert len(choices) == 12
    assert filtered_set.issubset(set(choices))
    choices = choices[10:]
    assert len(choices) == 2
    assert len(set(choices)) == len(choices)

def test_choose_get_index():
    lst = [1,2,2,3,4,4,4,5]
    init_len = len(lst)
    value = 4
    choice = choose_get_index(lst, value)
    assert choice in [4,5,6]
    assert len(lst) == init_len - 1

# def test_select_random_areas():
#     parent = AtlasModel.objects.get(pk='testgrid_1_atlasDXdHqPR3RhyJm9')
#     targets = parent.targets.all()
#     filtered = filter_targets(parent, targets)
#     choices = select_random_areas(targets, filtered, 3)
#     assert len(choices) == 3
#     assert len(set(choices)) == len(choices)
#     choices = choices[1:]
#     assert len(choices) == 2
#     assert len(set(choices)) == len(choices)

#     assert len(targets) == len(filtered), f'Length of targets {len(targets)} and filtered {len(filtered)} do not match.'