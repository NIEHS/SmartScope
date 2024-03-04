import numpy as np
import logging
from ..mesh_operations import get_average_angle, filter_closest

logger = logging.getLogger(__name__)

def get_mesh_rotation_spacing(targets, mesh_spacing_in_pixels):
    # grid = AutoloaderGrid.objects.get(pk=grid_id)
    # print(f'Finding points within {mesh_spacing_in_pixels} pixels.')
    filtered_points, spacing= filter_closest(targets, mesh_spacing_in_pixels*1.08)
    logging.debug(f'Calculated mean spacing: {spacing} pixels')
    rotation = get_average_angle(filtered_points)
    logging.debug(f'Calculated mesh rotation: {rotation} degrees')
    return rotation, spacing

def lattice_extension(input_lattice:np.ndarray, image:np.ndarray, expected_spacing_in_pixels:float):
    rotation, spacing = get_mesh_rotation_spacing(input_lattice,mesh_spacing_in_pixels=expected_spacing_in_pixels)


