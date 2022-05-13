from pandas import isnull
from Smartscope.lib.montage import Hole, Square
from django.contrib.auth.models import User, Group
from rest_framework import serializers as RESTserializers
from Smartscope.server.models import *
from Smartscope.server.lib.s3functions import *
import os
from Smartscope.lib.converters import *


# class ImageModelSerializer(RESTserializers.ModelSerializer):

#     def __init__(self, *args, **kwargs):
#         self.base_directory = kwargs.pop('base_directory',None)
#         self.base_url = kwargs.pop('base_url',None)
#         super().__init__(*args,**kwargs)

#     def get_full_path(self, data):
#         if self.is_aws:
#             storage = SmartscopeStorage()
#             if isinstance(data, dict):
#                 for k, v in data.items():
#                     data[k] = storage.url(v)
#                 return data
#             else:
#                 return storage.url(data)
#         return data

#     @property
#     def is_aws(self):
#         if os.path.isabs(self.base_directory):
#             return False
#         return True

#     # @property
#     # def directory(self):
#     #     return os.path.join(self.base_directory, self.name)


#     def get_svg(self,obj):
#         return os.path.join(self.base_directory, 'pngs', f'{obj.name}.svg')


#     def get_png(self,obj):
#         return dict(path=os.path.join(self.base_directory, 'pngs', f'{obj.name}.png'),
#                     url=self.get_full_path(os.path.join(self.base_url, 'pngs', f'{obj.name}.png')))


#     def get_mrc(self,obj):
#         return os.path.join(self.base_directory, obj.name, f'{obj.name}.mrc')


#     def get_raw_mrc(self,obj):
#         return os.path.join(self.base_directory, 'raw', f'{obj.name}.mrc')


#     def get_ctf_img(self,obj):
#         # img_path = os.path.join(self.directory, 'ctf.png')
#         # if os.path.isfile(img_path):
#         return self.get_full_path(os.path.join(self.base_url,obj.name, 'ctf.png'))


class UserSerializer(RESTserializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'groups']


class GroupSerializer(RESTserializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name']


class MicroscopeSerializer(RESTserializers.ModelSerializer):
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


class AutoloaderGridSerializer(RESTserializers.ModelSerializer):
    # directory = RESTserializers.ReadOnlyField()

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


class AtlasSerializer(RESTserializers.ModelSerializer):
    id = RESTserializers.ReadOnlyField()
    # parent = RESTserializers.ReadOnlyField()
    # grid_id = AutoloaderGridSerializer()
    # svg = RESTserializers.ReadOnlyField()
    # png = RESTserializers.ReadOnlyField()
    # raw = RESTserializers.ReadOnlyField()
    # mrc = RESTserializers.ReadOnlyField()
    # selectors = RESTserializers.ReadOnlyField()
    # classifiers = RESTserializers.ReadOnlyField()
    targets_methods = RESTserializers.ReadOnlyField()

    class Meta:
        model = AtlasModel
        fields = '__all__'
        extra_fields = ['id', 'targets_methods']  # ['svg', 'png', 'raw', 'mrc']


class FilePathsSerializer(RESTserializers.Serializer):

    def to_representation(self, instance):
        data = dict()
        for k, _ in self.context['request'].query_params.items():
            data[k] = getattr(instance, k)

        # if not os.path.isabs(instance.directory):
        #     storage = SmartscopeStorage()
        #     for k, v in data.items():
        #         if isinstance(v, dict):
        #             for k1, v1 in v.items():
        #                 data[k][k1] = storage.url(v1)
        #         else:
        #             data[k] = storage.url(v)

        return data


class FilePathSerializer(RESTserializers.Serializer):
    def to_representation(self, instance):
        return get_file_path(instance, instance)


class SquareSerializer(RESTserializers.ModelSerializer):
    id = RESTserializers.ReadOnlyField()
    # parent = RESTserializers.ReadOnlyField()
    # grid_id = AutoloaderGridSerializer()
    # atlas_id = AtlasSerializer()
    # initial = RESTserializers.ReadOnlyField(source='initial_quality')
    # svg = RESTserializers.ReadOnlyField()
    has_queued = RESTserializers.ReadOnlyField()
    has_completed = RESTserializers.ReadOnlyField()
    has_active = RESTserializers.ReadOnlyField()

    class Meta:
        model = SquareModel
        fields = '__all__'
        extra_fields = ['id']
        # fields = ['square_id', 'initial']
        # extra_fields = ['initial', 'svg', 'png', 'raw', 'mrc']


class HighMagSerializer(RESTserializers.ModelSerializer):
    id = RESTserializers.ReadOnlyField()
    # svg = RESTserializers.ReadOnlyField()
    png = RESTserializers.ReadOnlyField()
    # hole_id = HoleSerializer()
    ctf_img = RESTserializers.ReadOnlyField()
    # raw = RESTserializers.ReadOnlyField()
    # mrc = RESTserializers.ReadOnlyField()
    # initial = RESTserializers.ReadOnlyField(source='initial_quality')

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
    # parent = RESTserializers.ReadOnlyField()
    # svg = RESTserializers.ReadOnlyField()
    # png = RESTserializers.SerializerMethodField()
    # raw = RESTserializers.ReadOnlyField()
    # mrc = RESTserializers.ReadOnlyField()
    # initial = RESTserializers.ReadOnlyField(source='initial_quality')
    # high_mag = RESTserializers.SerializerMethodField()

    # def get_png(self,obj):
    #     if obj.status == 'completed':
    #         return obj.png

    def get_high_mag(self, obj):
        if obj.status == 'completed':
            return HighMagSerializer(obj.high_mag, many=False).data

    class Meta:
        model = HoleModel
        fields = '__all__'
        extra_fields = ['id']
        # extra_fields = ['high_mag', 'initial', ]  # 'svg', 'png', 'raw', 'mrc']


class DetailedHoleSerializer(RESTserializers.ModelSerializer):
    id = RESTserializers.ReadOnlyField()
    # parent = RESTserializers.ReadOnlyField()
    # svg = RESTserializers.ReadOnlyField()
    # png = RESTserializers.SerializerMethodField()
    # raw = RESTserializers.ReadOnlyField()
    # mrc = RESTserializers.ReadOnlyField()
    # initial = RESTserializers.ReadOnlyField(source='initial_quality')
    high_mag = HighMagSerializer(many=False)

    # def get_png(self,obj):
    #     if obj.status == 'completed':
    #         return obj.png

    # def get_high_mag(self, obj):
    #     if obj.status == 'completed':
    #         return HighMagSerializer(obj.high_mag, many=False).data

    class Meta:
        model = HoleModel
        fields = '__all__'
        extra_fields = ['id']
        extra_fields = ['high_mag']  # 'svg', 'png', 'raw', 'mrc']


class HoleSerializerSimple(RESTserializers.ModelSerializer):
    grid_id = AutoloaderGridSerializer()
    # square_id = SquareSerializer()

    class Meta:
        model = HoleModel
        fields = ['hole_id', 'number', 'name', 'square_id', 'grid_id']


class FullGridSerializer(RESTserializers.ModelSerializer):
    atlas = AtlasSerializer(many=True)
    squares = SquareSerializer(many=True)
    # holes = HoleSerializer(many=True)
    # high_mag = HighMagSerializer(many=True)

    # def get_atlas(self, obj):
    #     return AtlasSerializer(obj.atlas, many=True)

    # def get_squares(self, obj):
    #     squares_data = SquareSerializer(obj.squares, many=True)
    #     output = dict()
    #     for i in squares_data.data:
    #         output[i['id']] = i
    #     return output

    # def get_holes(self, obj):
    #     return HoleSerializer(obj.holes, many=True, base_directory=obj.directory, base_url=obj.url).data
    #     # output = dict()
    #     # for i in holes_data.data:
    #     #     output[i['id']] = i
    #     # return output

    class Meta:
        model = AutoloaderGrid
        fields = '__all__'
        extra_fields = ['atlas', 'squares']


class ExportMetaSerializer(RESTserializers.ModelSerializer):
    atlas = AtlasSerializer(many=True)
    squares = SquareSerializer(many=True)
    holes = HoleSerializer(many=True)
    high_mag = HighMagBasicSerializer(many=True)
    params_id = GridCollectionParamsSerializer(many=False)

    class Meta:
        model = AutoloaderGrid
        fields = '__all__'
        extra_fields = ['atlas', 'squares', 'holes', 'high_mag']


models_to_serializers = {
    'AutoloaderGrid': {'key': 'grid', 'serializer': AutoloaderGridSerializer, 'element': None},
    'AtlasModel': {'key': 'atlas', 'serializer': AtlasSerializer, 'element': '#Atlas_im'},
    'SquareModel': {'key': 'squares', 'serializer': SquareSerializer, 'element': '#Square_im'},
    'HoleModel': {'key': 'holes', 'serializer': HoleSerializer, 'element': 'hole'},
}


class SvgSerializer(RESTserializers.Serializer):

    def __init__(self, display_type=None, method=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.targetSerializer = targetSerializer
        self.display_type = display_type
        self.method = method

    def read_svg(self):

        if self.instance.is_aws:
            storage = SmartscopeStorage()
            # print(self.instance.svg)
            with storage.open(self.instance.svg, 'r') as f:
                url = self.instance.png['url']
                # print(url)
                return f.read().replace(f'{self.instance.name}.png', url)
        with open(self.instance.svg, 'r') as f:
            return f.read().replace(f'{self.instance.name}.png', self.instance.png['url'])

    def load_meta(self):
        # json_meta = dict()
        targets = self.instance.targets
        return update_to_fullmeta(targets)

    def to_representation(self, instance):
        # try:
        #     if self.context['request'].query_params['metaonly'] == 'true':
        #         return {
        #             'fullmeta': self.load_meta(),
        #         }
        # except:
        #     pass
        # display_type = isnull_to_none(self.context['request'].query_params['display_type'])
        # display_type = 'classifiers' if display_type is None else display_type
        # method = isnull_to_none(self.context['request'].query_params['method'])
        # logger.debug(self.context['request'].query_params)
        return {
            'type': 'reload',
            'display_type': self.display_type,
            'method': self.method,
            'element': models_to_serializers[self.instance.__class__.__name__]['element'],
            'svg': self.instance.toSVG(display_type=self.display_type, method=self.method,),
            'fullmeta': self.load_meta()
        }


def update_to_fullmeta(objects: list):
    classname = objects[0].__class__.__name__
    updateDict = dict()
    if classname == 'AutoloaderGrid':
        return models_to_serializers[classname]['serializer'](objects[0], many=False).data
    serialized_obj = list_to_dict(models_to_serializers[classname]['serializer'](objects, many=True).data)
    updateDict[models_to_serializers[classname]['key']] = serialized_obj
    if classname == 'HoleModel':
        serialized_obj = list_to_dict(models_to_serializers['SquareModel']['serializer'](
            [objects[0].square_id], many=True).data)
        updateDict[models_to_serializers['SquareModel']['key']] = serialized_obj
    # if classname == 'AtlasModel':
    #     serialized_obj = list_to_dict(models_to_serializers['AtlasModel']['serializer'](
    #         objects[0], many=True).data)
    #     updateDict[models_to_serializers[classname]['key']] = serialized_obj
    return updateDict
