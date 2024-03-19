import Smartscope.bin.smartscope

from Smartscope.core.data_manipulations import get_target_methods, filter_targets, randomized_choice, choose_get_index
from Smartscope.core.models import SquareModel

def test_get_target_methods():
    parent = SquareModel.objects.get(pk='grid1_square11BeZGKcjKyUKT3nQh')
    methods = get_target_methods(parent, 'selectors')
    assert len(methods) == 1

def test_filter_targets():
    parent = SquareModel.objects.get(pk='grid1_square11BeZGKcjKyUKT3nQh')
    filtered,filtered_set = filter_targets(parent)
    assert len(filtered_set) == 5

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