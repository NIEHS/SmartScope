'''
demo testing cases
'''
from .commons import *


class TestImport(TestCase):
    def test_(self):
        assert True == True

    def test_func(self):
        assert func_() == None
    
    @mock.patch.dict(os.environ, {'TEST': 'dev'})
    def test_env(self):
        res = os.environ.get('TEST')
        assert res == 'dev'
