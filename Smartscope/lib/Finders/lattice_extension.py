import numpy as np
import logging
from ..mesh_operations import generate_rotated_grid, calculate_translation, remove_indices, filter_oob
from .basic_finders import create_square_mask

logger = logging.getLogger(__name__)

def lattice_extension(input_lattice:np.ndarray, image:np.ndarray, rotation:float, spacing:float):
    points = generate_rotated_grid(spacing, rotation, image.shape)
    translation, _ = calculate_translation(input_lattice,points.T)
    translated = points + translation.reshape(2,-1)
    translation, min_idx = calculate_translation(input_lattice,translated.T)
    translated = remove_indices(translated.T, min_idx)
    translated = filter_oob(translated,image.shape)
    translated = translated.astype(int)
    mask = create_square_mask(image=image)
    filtered = translated[np.where(mask[translated[:,1],translated[:,0]] == 1)]
    return filtered
    # return filtered, True, dict(spacing=spacing, rotation=rotation, translation=translation)
