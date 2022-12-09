from rest_framework.serializers import ModelSerializer
from Smartscope.core import models
from Smartscope.server.api.serializers import GridCollectionParamsSerializer
from django.contrib.contenttypes.models import ContentType
from django.db import transaction


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
    finders = FinderSerializer(many=True)
    selectors = SelectorSerializer(many=True)
    classifiers = ClassifierSerializer(many=True)


class DetailedHighMagSerializer(TargetSerializer):

    class Meta:
        model = models.HighMagModel
        exclude = ['hm_id','hole_id','grid_id']

class DetailedHoleSerializer(TargetSerializer):
    targets = DetailedHighMagSerializer(many=True)

    class Meta:
        model = models.HoleModel
        exclude = ['hole_id','square_id','grid_id']

class DetailedSquareSerializer(TargetSerializer):
    targets = DetailedHoleSerializer(many=True)

    class Meta:
        model = models.SquareModel
        exclude = ['square_id','atlas_id','grid_id']

class DetailedAtlasSerializer(ModelSerializer):
    targets = DetailedSquareSerializer(many=True)

    class Meta:
        model = models.AtlasModel
        exclude = ['atlas_id','grid_id']

def extract_targets(data):
    target_labels= []
    target_labels += [(item,models.Finder) for item in data.pop('finders',[])]
    target_labels += [(item,models.Classifier) for item in data.pop('classifiers',[])]
    target_labels += [(item,models.Selector) for item in data.pop('selectors',[])]
    targets = data.pop('targets',[])
    return target_labels, data, targets

def create_target_label_instances(target_labels,instance,content_type):
    target_labels_models = []
    for label,label_class in target_labels:
        target_labels_models.append(label_class(**label,object_id=instance,content_type=content_type))    
    return target_labels_models

class ExportMetaSerializer(ModelSerializer):
    atlas = DetailedAtlasSerializer(many=True)
    params_id = GridCollectionParamsSerializer()

    class Meta:
        model = models.AutoloaderGrid
        exclude = ['grid_id']
        extra_fields = ['atlas']

    def create(self,validated_data):
        atlas = validated_data.pop('atlas')[0]
        params_id = validated_data.pop('params_id')
        params_id_model,created = models.GridCollectionParams.objects.get_or_create(**params_id)
        grid_model = models.AutoloaderGrid(**validated_data, params_id=params_id_model)
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


