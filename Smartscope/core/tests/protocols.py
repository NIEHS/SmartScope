import Smartscope.bin.smartscope
from ..run_grid import parse_method, runAcquisition
from ..interfaces.utils import generate_mock_fake_scope_interface


def test_parse_method_string():
    method, content, args, kwargs = parse_method('atlas')
    assert method == 'atlas'
    assert args == []
    assert kwargs == {}

def test_parse_method_dict():
    method, content, args, kwargs = parse_method({'call': {'script':'loadGrid',
                                                            'args': [1,2,3], 
                                                            'kwargs':{'position': 1}}})
    assert method == 'call'
    assert content == {'script':'loadGrid',}
    assert args == [1,2,3]
    assert kwargs == {'position':1}


def test_run_acquisition():
    scope = generate_mock_fake_scope_interface()
    output = runAcquisition(scope, 
                   [{'call': {'script':'loadGrid',
                            'args': [1,2,3], 
                            'kwargs':{'position': 1}}}],
                    params=None, instance=None,)
    assert output is None
