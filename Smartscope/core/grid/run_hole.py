'''
'''

from numpy.typing import ArrayLike
from typing import List, Union
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

from .finders import find_targets
from .transformations import register_to_other_montage, register_targets_by_proximity, recenter_targets
from .diagnostics import generate_diagnostic_figure, Timer


from Smartscope.core.models.hole import HoleModel
from Smartscope.core.models.high_mag import HighMagModel
from Smartscope.core.status import status
from Smartscope.core.protocols import get_or_set_protocol
from Smartscope.core.db_manipulations import update, add_targets


from Smartscope.lib.image_manipulations import auto_contrast_sigma, fourier_crop, export_as_png
from Smartscope.lib.image.montage import Montage
from Smartscope.lib.image.targets import Targets


# for arguments
from Smartscope.lib.multishot import MultiShot
from Smartscope.lib.image.target import Target

from .run_io import get_file_and_process

class RunHole:
    
    @staticmethod
    def process_hole_image(hole, grid, microscope_id):
        with Timer(text='Processing hole') as timer:
            protocol = get_or_set_protocol(grid).mediumMag
            params = grid.params_id
            logger.debug(f'Acquisition parameters: {params.params_id}')
            mutlishot_file = Path(grid.directory,'multishot.json')
            multishot = RunHole.load_multishot_from_file(mutlishot_file)
            if multishot is not None:
                logger.info(f'Multishot enabled: {params.multishot_per_hole}, ' + \
                    'Shots: {multishot.shots}, File: {mutlishot_file}')
            montage = get_file_and_process(
                hole.raw,
                hole.name,
                directory=microscope_id.scope_path,
                force_reprocess=True
            )
            export_as_png(
                montage.image,
                montage.png,
                normalization=auto_contrast_sigma,
                binning_method=fourier_crop
            )
            timer.report_timer('Getting and processing montage')
            if hole.bis_group is not None:
                hole_group = list(
                    HoleModel.display.filter(
                        square_id=hole.square_id,
                        bis_group=hole.bis_group
                    )
                )
            else:
                hole_group = [hole]
            hole.targets.delete()
            timer.report_timer('Querying and deleting previous targerts in BIS group')
            square_montage = Montage(
                name=hole.square_id.name,
                working_dir=hole.grid_id.directory
            )
            square_montage.load_or_process()
            image_coords = register_to_other_montage(np.array([x.coords for x in hole_group]),hole.coords, montage, square_montage)
            timer.report_timer('Initial registration to the higher mag image')
            targets = []
            finder_method = 'Registration'
            classifier_method=None
            if len(protocol.targets.finders) != 0:
                targets, finder_method, classifier_method, additional_outputs = find_targets(
                    montage, protocol.targets.finders
                )
                generate_diagnostic_figure(
                    montage.image,
                    [([montage.center],(0,255,0), 1), ([t.coords for t in targets],(0,0,255),1)],
                    Path(montage.directory / f'hole_recenter_it.png')
                )
                
            if len(protocol.targets.finders) == 0 or targets == []:
                targets = Targets.create_targets_from_center(image_coords, montage)
            timer.report_timer('Identifying and registering targets')
            targets_coords = np.array([target.coords for target in targets])
            register = register_targets_by_proximity(
                targets = image_coords,
                new_targets= recenter_targets(targets_coords, montage.center),
            )
            for h, index in zip(hole_group,register):
                target = targets[index]
                if not params.multishot_per_hole:
                    targets_to_register=[target]
                else:
                    targets_to_register= RunHole.split_target_for_multishot(multishot,target.coords,montage)
                add_targets(
                    grid,
                    h,
                    targets_to_register,
                    HighMagModel,
                    finder_method,
                    classifier=classifier_method
                )
            timer.report_timer('Final registration and saving to db')
            update(hole,
                shape_x=montage.shape_x,
                shape_y=montage.shape_y,
                pixel_size=montage.pixel_size,
                status=status.PROCESSED
            )

    @staticmethod
    def load_multishot_from_file(file:Union[str,Path]) -> Union[MultiShot,None]:
        if Path(file).exists():
            return MultiShot.parse_file(file)
    

    @staticmethod
    def split_target_for_multishot(
            shots:MultiShot,
            target_coords:ArrayLike,
            montage: Montage
        ) -> List[Target]:
        shots_in_pixels = shots.convert_shots_to_pixel(montage.pixel_size / 10_000) + target_coords
        return Targets.create_targets_from_center(shots_in_pixels,montage)
