from django.contrib.auth.models import User, Group
from rest_framework import serializers as RESTserializers
# from Smartscope.core.model import *
from Smartscope.core.models.microscope import Microscope
from Smartscope.core.models.detector import Detector
from Smartscope.core.models.screening_session import ScreeningSession
from Smartscope.core.models.grid import AutoloaderGrid
from Smartscope.core.models.hole_type import HoleType
from Smartscope.core.models.hole import HoleModel
from Smartscope.core.models.grid_collection_params import GridCollectionParams
from Smartscope.core.models.mesh import MeshMaterial, MeshSize
from Smartscope.core.models.atlas import AtlasModel
from Smartscope.core.models.square import SquareModel
from Smartscope.core.models.high_mag import HighMagModel
from Smartscope.core.models.target_label import Classifier
from Smartscope.lib.Datatypes.selector_sorter import SelectorSorter, LagacySorterError
from Smartscope.core.settings.worker import PLUGINS_FACTORY
from Smartscope.core.svg_plots import drawAtlasNew
# from Smartscope.lib.storage.smartscope_storage import SmartscopeStorage
from Smartscope.lib.converters import *
import logging

logger = logging.getLogger(__name__)


class UserSerializer(RESTserializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'groups']


class GroupSerializer(RESTserializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name']


class MicroscopeSerializer(RESTserializers.ModelSerializer):
    # 
    class Meta:
        model = Microscope
        fields = '__all__'


class DetectorSerializer(RESTserializers.ModelSerializer):
    class Meta:
        model = Detector
        fields = '__all__'


class SessionSerializer(RESTserializers.ModelSerializer):
    class Meta:
        model = ScreeningSession
        fields = '__all__'

class ClassifierSerializer(RESTserializers.ModelSerializer):

    class Meta:
        model = Classifier
        exclude = ['id']


class AutoloaderGridSerializer(RESTserializers.ModelSerializer):

    class Meta:
        model = AutoloaderGrid
        fields = '__all__'


class MeshMaterialSerializer(RESTserializers.ModelSerializer):
    class Meta:
        model = MeshMaterial
        fields = '__all__'


class MeshSizeSerializer(RESTserializers.HyperlinkedModelSerializer):
    class Meta:
        model = MeshSize
        fields = '__all__'


class HoleTypeSerializer(RESTserializers.ModelSerializer):
    class Meta:
        model = HoleType
        fields = '__all__'


class GridCollectionParamsSerializer(RESTserializers.ModelSerializer):
    class Meta:
        model = GridCollectionParams
        fields = '__all__'


# class FinderSerializer(RESTserializers.ModelSerializer):

#     class Meta:
#         model = Finder
#         # fields = '__all__'
#         exclude = ['id', ]


# class ClassifierSerializer(RESTserializers.ModelSerializer):

#     class Meta:
#         model = Classifier
#         # fields = '__all__'
#         exclude = ['id', ]


# class SelectorSerializer(RESTserializers.ModelSerializer):

#     class Meta:
#         model = Selector
#         # fields = '__all__'
#         exclude = ['id', ]


class AtlasSerializer(RESTserializers.ModelSerializer):
    id = RESTserializers.ReadOnlyField()

    class Meta:
        model = AtlasModel
        fields = '__all__'
        extra_fields = ['id',]


class FilePathsSerializer(RESTserializers.Serializer):

    def to_representation(self, instance):
        data = dict()
        for k, _ in self.context['request'].query_params.items():
            data[k] = getattr(instance, k)

        return data


class FilePathSerializer(RESTserializers.Serializer):
    def to_representation(self, instance):
        return get_file_path(instance, instance)


class SquareSerializer(RESTserializers.ModelSerializer):
    id = RESTserializers.ReadOnlyField()
    # has_queued = RESTserializers.ReadOnlyField()
    # has_completed = RESTserializers.ReadOnlyField()
    # has_active = RESTserializers.ReadOnlyField()

    class Meta:
        model = SquareModel
        fields = '__all__'
        extra_fields = ['id']
        # fields = ['square_id', 'initial']
        # extra_fields = ['initial', 'svg', 'png', 'raw', 'mrc']


class HighMagSerializer(RESTserializers.ModelSerializer):
    # id = RESTserializers.ReadOnlyField()
    # svg = RESTserializers.ReadOnlyField()
    # png = RESTserializers.ReadOnlyField()
    # hole_id = HoleSerializer()
    # ctf_img = RESTserializers.ReadOnlyField()


    class Meta:
        model = HighMagModel
        fields = '__all__'
        # extra_fields = ['png']  # 'svg', 'png', 'raw', 'mrc']


class HighMagBasicSerializer(RESTserializers.ModelSerializer):

    class Meta:
        model = HighMagModel
        fields = '__all__'


class HoleSerializer(RESTserializers.ModelSerializer):
    id = RESTserializers.ReadOnlyField()

    # def get_high_mag(self, obj):
    #     if obj.status == 'completed':
    #         return HighMagSerializer(obj.high_mag, many=False).data

    class Meta:
        model = HoleModel
        fields = '__all__'
        extra_fields = ['id']


# class TargetSerializer(RESTserializers.ModelSerializer):
#     finders = FinderSerializer(many=True)
#     selectors = SelectorSerializer(many=True)
#     classifiers = ClassifierSerializer(many=True)


# class DetailedHighMagSerializer(TargetSerializer):

#     class Meta:
#         model = HighMagModel
#         fields = '__all__'

# class DetailedHoleSerializer(TargetSerializer):
#     targets = DetailedHighMagSerializer(many=True)

#     class Meta:
#         model = HoleModel
#         fields = '__all__'

# class DetailedSquareSerializer(TargetSerializer):
#     targets = DetailedHoleSerializer(many=True)

#     class Meta:
#         model = SquareModel
#         fields = '__all__'

# class DetailedAtlasSerializer(RESTserializers.ModelSerializer):
#     targets = DetailedSquareSerializer(many=True)

#     class Meta:
#         model = AtlasModel
#         fields = '__all__'

class HoleSerializerSimple(RESTserializers.ModelSerializer):
    grid_id = AutoloaderGridSerializer()

    class Meta:
        model = HoleModel
        fields = ['hole_id', 'number', 'name', 'square_id', 'grid_id']


class FullGridSerializer(RESTserializers.ModelSerializer):
    atlas = AtlasSerializer(many=True)
    squares = SquareSerializer(many=True)

    class Meta:
        model = AutoloaderGrid
        fields = '__all__'
        extra_fields = ['atlas', 'squares']

# class ExportMetaSerializer(RESTserializers.ModelSerializer):
#     atlas = DetailedAtlasSerializer(many=True)

#     class Meta:
#         model = AutoloaderGrid
#         fields = '__all__'
#         extra_fields = ['atlas']


models_to_serializers = {
    'AutoloaderGrid': {'key': 'grid', 'serializer': AutoloaderGridSerializer, 'element': None},
    'AtlasModel': {'key': 'atlas', 'serializer': AtlasSerializer, 'element': '#Atlas_im'},
    'SquareModel': {'key': 'squares', 'serializer': SquareSerializer, 'element': '#Square_im'},
    'HoleModel': {'key': 'holes', 'serializer': HoleSerializer, 'element': 'hole'},
}


class SvgSerializer(RESTserializers.Serializer):

    def __init__(self, display_type=None, method=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.display_type = display_type
        self.method = method

    # def read_svg(self):

    #     if self.instance.is_aws:
    #         storage = SmartscopeStorage()
    #         with storage.open(self.instance.svg, 'r') as f:
    #             url = self.instance.png['url']
    #             return f.read().replace(f'{self.instance.name}.png', url)
    #     with open(self.instance.svg, 'r') as f:
    #         return f.read().replace(f'{self.instance.name}.png', self.instance.png['url'])

    def load_meta(self):
        targets = self.instance.targets
        if len(targets) == 0:
            return dict()
        return update_to_fullmeta(targets)

    def svg(self):
        if self.display_type == 'selectors':
            try:
                sorter = SelectorSorter(PLUGINS_FACTORY[self.method], list(self.instance.targets), n_classes=5, from_server=True)
                return drawAtlasNew(self.instance, sorter).as_svg()
            except LagacySorterError:
                logger.warning('Lagacy sorter error. Reverting to lagacy sorting.')
        return self.instance.svg(display_type=self.display_type, method=self.method,).as_svg()
        

    def to_representation(self, instance):
        return {
            'type': 'reload',
            'display_type': self.display_type,
            'method': self.method,
            'element': models_to_serializers[self.instance.__class__.__name__]['element'],
            'svg': self.svg()
            # 'fullmeta': self.load_meta()
        }


def update_to_fullmeta(objects: list):
    updateDict = dict(atlas=[], squares=[], holes=[])
    for obj in objects:
        classname = obj.__class__.__name__
        if classname == 'AutoloaderGrid':
            updateDict.update(models_to_serializers[classname]['serializer'](obj, many=False).data)
            continue
        if classname in models_to_serializers.keys():
            updateDict[models_to_serializers[classname]['key']].append(obj)
        if classname == 'HoleModel' and (square := obj.square_id) not in updateDict['squares']:
            updateDict['squares'].append(square)
    updateDict['atlas'] = list_to_dict(models_to_serializers['AtlasModel']['serializer'](updateDict['atlas'], many=True).data)
    updateDict['squares'] = list_to_dict(models_to_serializers['SquareModel']['serializer'](updateDict['squares'], many=True).data)
    updateDict['holes'] = list_to_dict(models_to_serializers['HoleModel']['serializer'](updateDict['holes'], many=True).data)
    return updateDict
