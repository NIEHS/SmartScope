from django.test import TestCase
import os
TESTS_DIR = os.path.dirname(os.path.dirname(__file__))
TESTS_DATA_DIR = os.path.join(TESTS_DIR, 'data')
os.chdir(TESTS_DATA_DIR)

from Smartscope.core.models import Target, Finder

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey

# class TargetX(models.Model):
#     name = models.CharField(max_length=100)
#     finders = GenericRelation(Finder)
#     class Meta:
#         app_label='API'


class TestFinder(TestCase):

    def setUp(self):
        pass
        # square = SquareModel.objects.create(
        #     name='grid1_square0',
        #     number=0,
        #     selected=0,
        #     square_id='grid1_square0O6jCP1se1Bde2uvuP',
        #     area=515872,
        #     atlas_id_id='grid1_atlasFCRZz1LkKCDJ86XaaWl',
        #     grid_id_id='1grid1Yoea1ZJGXxgAveV41PnCWHHX'
        # )
        ContentType.objects.get(
            app_label='API',
            model='squaremodel'
        )
        finder = Finder.objects.create(
            # content_id='grid1_square0O6jCP1se1Bde2uvuP',
            content_type_id=14,
            # content_object = square,
            method_name='AI square finder',
            x=6880, 
            y=329,
            stage_x=305.976,
            stage_y=121.678,
            stage_z=-7.64184, 
        )

    def test_finder(self):
        # post = BlogPost.objects.get(pk=1)
        # comment = Comment.objects.create(content_object=post, text='Great post!')
        # print(post.comments.all())
        # target = Target.display
        # res = Finder.objects.get(x=6880)
        # # assert res.x == 6880
        # print(f"###{target}###")
        pass