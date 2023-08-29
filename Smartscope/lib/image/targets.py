
from typing import List
import logging

from .base_image import BaseImage
from .target import Target


logger = logging.getLogger(__name__)

class Targets:

    @staticmethod
    def create_targets_from_box(
            targets: List,
            montage: BaseImage,
            target_type: str = 'square'
        ):
        output_targets = []
        if isinstance(targets, tuple):
            targets, labels = targets
        else:
            labels = [None] * len(targets)
        for target, label in zip(targets, labels):
            t = Target(target, quality=label)
            t.convert_image_coords_to_stage(montage)
            t.set_area_radius(target_type)
            output_targets.append(t)

        output_targets.sort(key=lambda x: (x.stage_x, x.stage_y))
        return output_targets

    @staticmethod
    def create_targets_from_center(targets: List, montage: BaseImage):
        output_targets = []
        for target in targets:
            t = Target(target,from_center=True)
            t.convert_image_coords_to_stage(montage)
            output_targets.append(t)

        output_targets.sort(key=lambda x: (x.stage_x, x.stage_y))
        return output_targets