from django.test import TestCase
import os
TESTS_DIR = os.path.dirname(os.path.dirname(__file__))
TESTS_DATA_DIR = os.path.join(TESTS_DIR, 'data')
os.chdir(TESTS_DATA_DIR)

from Smartscope.core.models import Finder

class TestTarget(TestCase):

    def setUp(self):
        Target.objects.create(
            name='200',
            square_size=90,
            bar_width=35,
            pitch=125
        )

    def test_group(self):
        res = Target.objects.get(name='200')
        print(f"###{res.name}###")