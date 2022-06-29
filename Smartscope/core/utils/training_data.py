import math
import shutil

import yaml
from Smartscope.core.models import AtlasModel, SquareModel, DisplayManager
from pathlib import Path

mag_level_factory = {'atlas': AtlasModel, 'square': SquareModel}


def get_bounding_box(x, y, radius):
    return [x - radius, y - radius, x + radius, y + radius]


def generate_training_data(instance):
    query = instance.base_target_query(manager='display').all()

    training_data = []
    for target in query:
        finder = target.finders.first()
        x, y = finder.x, finder.y

        label = target.classifiers.filter(method_name=finder.method_name).values_list('label', flat=True)
        if len(label) == 0:
            label = target.classifiers.filter(method_name='Micrographs curation').values_list('label', flat=True)
        if instance.targets_prefix == 'square':
            radius = math.sqrt(target.area) // 2
        else:
            radius = target.radius

        coordinates = get_bounding_box(x, y, radius)

        training_data.append(dict(coordinates=coordinates, label=label[0] if len(label) > 0 else None))

    return training_data


def export_training_data(data, instance, directory='/mnt/data/tmp/'):
    image = f'{instance.pk}.mrc'
    grid_type = instance.grid_id.meshMaterial.name
    detection_type = instance.targets_prefix
    shape_x = instance.shape_x
    shape_y = instance.shape_y
    output_dir = Path(directory, detection_type)
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / 'metadata.yaml', 'a+') as file:
        file.write(yaml.dump([dict(image=image, shape_x=shape_x, shape_y=shape_y,
                   grid_type=grid_type, targets=data)], default_flow_style=None))

    shutil.copy(instance.mrc, output_dir / f'{instance.pk}.mrc')


def add_to_training_set(mag_level: str, id: str, output_directory='/mnt/data/training_data/'):
    instance = mag_level_factory[mag_level].objects.get(pk=id)
    data = generate_training_data(instance=instance)
    export_training_data(data, instance, directory=output_directory)
