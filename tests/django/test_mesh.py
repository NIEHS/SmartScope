from django.test import TestCase

from Smartscope.core.models import MeshSize, MeshMaterial

class TestMesh(TestCase):

    def setUp(self):
        MeshSize.objects.create(
            name='200',
            square_size=90,
            bar_width=35,
            pitch=125
        )
        MeshMaterial.objects.create(name='Carbon')

    def test_mesh_size(self):
        res = MeshSize.objects.get(name='200')
        assert res.name == '200'
        

    def test_mesh_material(self):
        res = MeshMaterial.objects.get(name='Carbon')
        assert res.name == 'Carbon'
