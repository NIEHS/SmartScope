import pytest
from Smartscope.bin import smartscope
from pathlib import Path

from ..models import HoleModel

from ..selector_sorter import SelectorSorter, SelectorSorterData, SelectorValueParser

def test_selector_sorter_init():
    sorter = SelectorSorter('selector_name', 5, [0,1])
    assert sorter.selector_name == 'selector_name'
    assert sorter._n_classes == 5
    assert sorter._fractional_limits == [0,1]

def test_selector_sorter_data_init():
    data = SelectorSorterData(selector_name='selector_name', low_limit=0, high_limit=1)
    assert data.selector_name == 'selector_name'
    assert data.low_limit == 0
    assert data.high_limit == 1

def test_selector_value_parser_init():
    parser = SelectorValueParser('selector_name', from_server=True)
    assert parser._selector_name == 'selector_name'
    assert parser._from_server == True

    parser = SelectorValueParser('selector_name', from_server=False)
    assert parser._selector_name == 'selector_name'
    assert parser._from_server == False

def test_selector_value_parsing():
    parser = SelectorValueParser('Graylevel selector', from_server=True)
    targets = HoleModel.display.filter(grid_id='1grid1OkinLNkbO4t1d8zuPKk3R5KE')
    assert all([isinstance(x, float) for x in parser.extract_values(targets)])

def test_selector_sorter_calculate_classes():
    n_classes = 5
    sorter = SelectorSorter('Graylevel selector', n_classes, [0,1])
    with pytest.raises(Exception):
        sorter.calculate_classes()

    sorter.values = [1,2,3,4,5,6,7,8,9,10]
    assert sorter.limits[0] == 1
    assert sorter.limits[-1] == 10
    sorter.calculate_classes()
    assert len(set(sorter._classes)) == 5

    sorter.limits = [3,9]
    assert sorter._classes is None
    sorter.calculate_classes()
    assert len(set(sorter._classes)) == 6

def test_selector_data_parse_sorter():
    sorter = SelectorSorter('Graylevel selector', 5, [0,1])
    sorter.values = [1,2,3,4,5,6,7,8,9,10]
    
    sorter_data = SelectorSorterData.parse_sorter(sorter)
    assert sorter_data.selector_name == 'Graylevel selector'
    assert sorter_data.low_limit == 1
    assert sorter_data.high_limit == 10

def test_selector_data_create_sorter():
    sorter_data = SelectorSorterData(selector_name='Graylevel selector', low_limit=0, high_limit=10)
    sorter = sorter_data.create_sorter()
    assert sorter.selector_name == 'Graylevel selector'
    assert sorter._n_classes == 5
    assert sorter.limits[0] == 0
    assert sorter.limits[-1] == 10

def test_selector_data_save_load():
    test_dir = Path('Smartscope/core/tests')
    sorter_data = SelectorSorterData(selector_name='Graylevel selector', low_limit=0, high_limit=10)
    sorter_data.save(test_dir)
    sorter_data = SelectorSorterData.load(test_dir, 'Graylevel selector')
    assert sorter_data.selector_name == 'Graylevel selector'
    assert sorter_data.low_limit == 0
    assert sorter_data.high_limit == 10
    sorter_data.delete(test_dir)