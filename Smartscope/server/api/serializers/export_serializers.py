from typing import List, Tuple, Union
from rest_framework.serializers import ModelSerializer, ListSerializer
from rest_framework import serializers as drf_serializers
from Smartscope.core import models
from .serializers import GridCollectionParamsSerializer, MicroscopeSerializer,DetectorSerializer, SquareSerializer, HoleSerializer, HighMagSerializer, AtlasSerializer
from .utils import extract_targets, create_target_label_instances
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class DetailedMicroscopeSerializer(ModelSerializer):

    class Meta:
        model = models.Microscope
        exclude = ['microscope_id']


class DetailedDetectorSerializer(ModelSerializer):
    microscope_id = DetailedMicroscopeSerializer()

    class Meta:
        model= models.Detector
        fields = '__all__'


class DetailedSessionSerializer(ModelSerializer):
    detector_id = DetailedDetectorSerializer()

    class Meta:
        model = models.ScreeningSession
        exclude = ['session_id','working_dir','microscope_id']


class FinderSerializer(ModelSerializer):

    class Meta:
        model = models.Finder
        exclude = ['id','object_id', 'content_type' ]


class ClassifierSerializer(ModelSerializer):

    class Meta:
        model = models.Classifier
        exclude = ['id', 'object_id', 'content_type']


class SelectorSerializer(ModelSerializer):

    class Meta:
        model = models.Selector
        exclude = ['id', 'object_id', 'content_type']

class TargetSerializer(ModelSerializer):
    name = drf_serializers.CharField(required=False)

    finders = FinderSerializer(many=True)
    selectors = SelectorSerializer(many=True, required=False)
    classifiers = ClassifierSerializer(many=True, required=False)

    class Config:
        id_alias:str = 'NotImplemented'
        target_model:models.BaseModel = 'NotImplemented'
        parent_model: models.BaseModel = 'NotImplemented'
        parent_id_alias:str = 'NotImplemented'

    def validate(self, attrs):
        return super().validate(attrs)

    def create(self,validated_data, label_types: Union[List, '__all__']= '__all__'):
        labels = []
        uid = validated_data.pop('uid')
        target_labels, validated_data, _ = extract_targets(validated_data, label_types= label_types)
        
        if uid is None:
            grid_id = models.AutoloaderGrid.objects.get(grid_id=validated_data.pop('grid_id'))
            parent_id = self.Config.parent_model.objects.get(pk=validated_data.pop(self.Config.parent_id_alias))
            instance = self.Meta.model(**validated_data, grid_id=grid_id, **{self.Config.parent_id_alias:parent_id})
            logger.debug(f'Created new instance with uid: {instance.pk}')
        else: 
            instance = self.Meta.model.objects.get(pk=uid)
            logger.debug(f'Working on target with uid: {instance.pk}')
       
        labels += create_target_label_instances(target_labels,instance.pk,ContentType.objects.get_for_model(self.Config.target_model))
        
        return instance, labels

    
class AddTargetsListSerializer(ListSerializer):

    def create(self, validated_data, label_types = '__all__',):
        all_targets = []
        all_labels = []
        for target in validated_data:
            instance, labels = self.child.create(target, label_types=label_types)
            all_targets.append(instance)
            all_labels += labels
        return all_targets, all_labels
    
    def update(self, validated_data):
        for target in validated_data:
            self.child.update(target)


class DetailedHighMagSerializer(TargetSerializer):

    class Meta:
        model = models.HighMagModel
        exclude = ['hm_id','hole_id','grid_id']

class DetailedHoleSerializer(TargetSerializer):
    targets = DetailedHighMagSerializer(many=True)

    class Meta:
        model = models.HoleModel
        exclude = ['hole_id','square_id','grid_id']


class DetailedFullHoleSerializer(TargetSerializer):
    targets = DetailedHighMagSerializer(many=True, required=False)

    class Meta:
        model = models.HoleModel
        fields = '__all__'
        list_serializer_class = AddTargetsListSerializer

    class Config:
        id_alias:str = 'hole_id'
        target_model:models.BaseModel = models.HoleModel
        parent_model: models.BaseModel = models.SquareModel
        parent_id_alias:str = 'square_id'

class ScipionPluginHoleSerializer(DetailedHoleSerializer):
    class Meta(DetailedHoleSerializer.Meta):
        exclude = []


class DetailedSquareSerializer(TargetSerializer):
    targets = DetailedHoleSerializer(many=True, )

    class Meta:
        model = models.SquareModel
        exclude = ['square_id','atlas_id','grid_id']
        

class DetailedFullSquareSerializer(TargetSerializer):
    targets = DetailedFullHoleSerializer(many=True, required=False)

    class Meta:
        model = models.SquareModel
        fields = '__all__'
        list_serializer_class = AddTargetsListSerializer

    class Config:
        id_alias:str = 'square_id'
        target_model:models.BaseModel = models.SquareModel
        parent_model: models.BaseModel = models.AtlasModel
        parent_id_alias:str = 'atlas_id'

class DetailedNoTargetSquareSerializer(TargetSerializer):
    # targets = DetailedHoleSerializer(many=True, required=False)

    class Meta:
        model = models.SquareModel
        fields = '__all__'
        list_serializer_class = AddTargetsListSerializer

    class Config:
        id_alias:str = 'square_id'
        target_model:models.BaseModel = models.SquareModel
        parent_model: models.BaseModel = models.AtlasModel
        parent_id_alias:str = 'atlas_id'

class DetailedAtlasSerializer(ModelSerializer):
    targets = DetailedSquareSerializer(many=True)

    class Meta:
        model = models.AtlasModel
        exclude = ['atlas_id','grid_id']

class DetailedFullAtlasSerializer(ModelSerializer):
    targets = DetailedNoTargetSquareSerializer(many=True)

    class Meta:
        model = models.AtlasModel
        fields = '__all__'

    class Config:
        id_alias:str = 'atlas_id'
        target_model:models.BaseModel = models.SquareModel


class ExportMetaSerializer(ModelSerializer):
    atlas = DetailedAtlasSerializer(many=True)
    params_id = GridCollectionParamsSerializer()
    session_id = DetailedSessionSerializer()

    class Meta:
        model = models.AutoloaderGrid
        exclude = ['grid_id']
        extra_fields = ['atlas']

    def create(self,validated_data):
        logger.debug(f"Importing {validated_data['name']}")
        session = validated_data.pop('session_id')
        detector_id = session.pop('detector_id')
        microscope_id = detector_id.pop('microscope_id')
        microscope_id_model,created = models.Microscope.objects.get_or_create(**microscope_id)
        logger.info(f'Microscope created: {created}')
        detector_id_model,created = models.Detector.objects.get_or_create(**detector_id, microscope_id=microscope_id_model)
        logger.info(f'Detector created: {created}')
        session_model, created = models.ScreeningSession.objects.get_or_create(**session, microscope_id = microscope_id_model, detector_id=detector_id_model)
        logger.info(f'Session created: {created}')
        atlas = validated_data.pop('atlas')[0]
        params_id = validated_data.pop('params_id')
        params_id_model,created = models.GridCollectionParams.objects.get_or_create(**params_id)
        logger.info(f'Params created: {created}')
        grid_model = models.AutoloaderGrid(**validated_data, params_id=params_id_model, session_id=session_model)
        squares = atlas.pop('targets')
        atlas_model = models.AtlasModel(**atlas, grid_id=grid_model)
        target_models = []

        target_labels_models = []
        square_content_type = ContentType.objects.get_for_model(models.SquareModel)
        hole_content_type = ContentType.objects.get_for_model(models.HoleModel)
        highmag_content_type = ContentType.objects.get_for_model(models.HighMagModel) 
        for square in squares:
            target_labels, square, holes = extract_targets(square)
            square_model = models.SquareModel(**square,grid_id=grid_model, atlas_id=atlas_model)
            target_models.append(square_model)
            target_labels_models += create_target_label_instances(target_labels,square_model.square_id,square_content_type)
            for hole in holes:
                target_labels, hole, highmags = extract_targets(hole)
                hole_model = models.HoleModel(**hole,grid_id=grid_model, square_id=square_model)
                target_models.append(hole_model)
                target_labels_models += create_target_label_instances(target_labels,hole_model.hole_id,hole_content_type)
                for highmag in highmags:
                    target_labels, highmag, _ = extract_targets(highmag)
                    highmag_model = models.HighMagModel(**highmag,grid_id=grid_model, hole_id=hole_model)
                    target_models.append(highmag_model)
                    target_labels_models += create_target_label_instances(target_labels,highmag_model.hm_id,highmag_content_type)
        with transaction.atomic():
            grid_model.save()
            atlas_model.save()
            [target.save() for target in target_models]
            [label.save() for label in target_labels_models]

        return grid_model