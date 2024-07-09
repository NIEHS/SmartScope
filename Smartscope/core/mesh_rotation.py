import numpy as np
import logging
from typing import Callable
from Smartscope.core.models import AutoloaderGrid, SquareModel, HoleModel
from Smartscope.lib.Datatypes.grid_geometry import GridGeometry, GridGeometryLevel
from Smartscope.lib.mesh_operations import filter_closest, get_average_angle, get_mesh_rotation_spacing
# from scipy.spatial import KDTree
# from scipy.signal import correlate2d
from scipy.spatial.distance import cdist #, pdist
# from skimage.transform import hough_line, hough_line_peaks
# from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)

def create_basic_mesh(spacing:float,size=10):
    a_range = np.arange(0, size, 1) *spacing 
    X, Y = np.meshgrid(a_range, a_range)
    points = np.vstack((X.ravel(), Y.ravel())).T
    return points


def hole_mesh(grid_instance):
    # square = SquareModel.display.filter(grid_id=grid_instance,status='completed').first()
    holes = HoleModel.display.filter(grid_id=grid_instance)
    holes = list(filter(lambda x: x.finders.all()[0].method_name != 'Regular pattern', holes))
    hole_spacing = grid_instance.holeType.pitch
    return holes, hole_spacing

def square_mesh(grid_instance):
    squares = SquareModel.display.filter(grid_id=grid_instance)
    square_spacing = grid_instance.meshSize.pitch
    return squares,square_spacing

def get_mesh_rotation(grid:AutoloaderGrid, level:Callable=hole_mesh, algo:Callable=get_average_angle):
    # grid = AutoloaderGrid.objects.get(pk=grid_id)
    targets, mesh_spacing = level(grid)
    stage_coords = np.array([t.stage_coords for t in targets])
    logger.debug(f'Found {len(targets)} targets. Mesh Spacing is {mesh_spacing} um.')
    filtered_points, _= filter_closest(stage_coords, mesh_spacing*1.08)
    rotation = algo(filtered_points)
    logger.debug(f'Calculated mesh rotation: {rotation}')
    return rotation


def calculate_hole_geometry(grid:AutoloaderGrid):
    targets, mesh_spacing = hole_mesh(grid)
    coords = np.array([t.coords for t in targets])
    pixel_size = targets[0].parent.pixel_size
    logger.debug(f'Calculating hole geometry for grid {grid} with {len(targets)} holes and mesh spacing: {mesh_spacing} um. Pixel size of {targets[0].parent}: {pixel_size} A.')
    rotation, spacing = get_mesh_rotation_spacing(coords, mesh_spacing / pixel_size * 10_000)
    
    geometry = GridGeometry.load(directory=grid.directory)
    geometry.set_geometry(level=GridGeometryLevel.SQUARE, spacing=spacing, rotation=rotation)
    geometry.save(directory=grid.directory)
    logger.info(f'Updated grid {grid} with rotation: {rotation} degrees and spacing: {spacing} pixels.')
    return rotation, spacing

def save_mm_geometry(grid:AutoloaderGrid):
    pass
    