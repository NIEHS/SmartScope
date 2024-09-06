'''
'''
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

from .finders import find_targets
from .run_io import get_file_and_process

from Smartscope.core.selectors import selector_wrapper
from Smartscope.core.models import HoleModel
from Smartscope.core.status import status
from Smartscope.core.protocols import get_or_set_protocol
from Smartscope.core.db_manipulations import update, add_targets, group_holes_from_square_for_BIS
from Smartscope.core.data_manipulations import select_n_areas
from Smartscope.lib.image_manipulations import export_as_png
from Smartscope.lib.image.montage import Montage

class RunSquare:

    @staticmethod
    def process_square_image(square, grid, microscope_id):
        protocol = get_or_set_protocol(grid).square.targets
        params = grid.params_id
        is_bis = params.bis_max_distance > 0
        montage = None
        if square.status == status.ACQUIRED:
            montage = get_file_and_process(
                raw=square.raw,
                name=square.name,
                directory=microscope_id.scope_path
            )
            export_as_png(montage.image, montage.png)
            targets, finder_method, classifier_method, _ = find_targets(montage, protocol.finders)
            holes = add_targets(grid, square, targets, HoleModel, finder_method, classifier_method)
            square = update(square,
                status=status.PROCESSED,
                shape_x=montage.shape_x,
                shape_y=montage.shape_y,
                pixel_size=montage.pixel_size,
                refresh_from_db=True
            )
            transaction.on_commit(lambda: logger.debug('targets added'))
        if square.status == status.PROCESSED:
            if montage is None:
                montage = Montage(name=square.name)
                montage.load_or_process()
            selector_wrapper(protocol.selectors, square, montage=montage)
            square = update(square, status=status.TARGETS_SELECTED)
            transaction.on_commit(lambda: logger.debug('Selectors added'))
        if square.status == status.TARGETS_SELECTED:
            group_holes_from_square_for_BIS(square, 
                                            max_radius=params.bis_max_distance,
                                            min_group_size=params.min_bis_group_size)
            logger.info(f'Picking holes on {square}')
            selected = select_n_areas(square, grid.params_id.holes_per_square, is_bis=is_bis)
            with transaction.atomic():
                for obj in selected:
                    update(obj, selected=True, status='queued')
            square = update(square, status=status.TARGETS_PICKED)
        if square.status == status.TARGETS_PICKED:
            square = update(square,
                status=status.COMPLETED,
                completion_time=timezone.now()
            )
        if square.status == status.COMPLETED:
            logger.info(f'Square {square.name} analysis is complete')

