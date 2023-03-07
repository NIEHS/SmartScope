import numpy as np
import logging
from typing import Callable
from Smartscope.core.models import AutoloaderGrid, SquareModel, HoleModel
from scipy.spatial import KDTree
from scipy.signal import correlate2d
from skimage.transform import hough_line, hough_line_peaks

logger = logging.getLogger(__name__)

def create_basic_mesh(spacing:float,size=10):
    a_range = np.arange(0, size, 1) *spacing 
    X, Y = np.meshgrid(a_range, a_range)
    points = np.vstack((X.ravel(), Y.ravel())).T
    return points


def hole_mesh(grid_instance):
    # square = SquareModel.display.filter(grid_id=grid_instance,status='completed').first()
    holes = HoleModel.display.filter(grid_id=grid_instance)   
    hole_spacing = grid_instance.holeType.pitch
    return holes, hole_spacing

def square_mesh(grid_instance):
    squares = SquareModel.display.filter(grid_id=grid_instance)
    square_spacing = grid_instance.meshSize.pitch
    return squares,square_spacing

def kabsch_rotation_2d(P, Q):
    """Kabsch algorithm implementation for 2D coordinates"""
    # center the point sets
    P_centered = P - np.mean(P, axis=0)
    Q_centered = Q - np.mean(Q, axis=0)
    # calculate the covariance matrix
    C = np.dot(np.transpose(P_centered), Q_centered)
    # singular value decomposition of the covariance matrix
    U, S, V = np.linalg.svd(C)
    # calculate the optimal rotation matrix
    R = np.dot(U, V)
    # calculate the rotation angle from the trace of R
    cos_theta = np.trace(R)
    sin_theta = R[1, 0] - R[0, 1]
    theta = np.degrees(np.arctan2(sin_theta, cos_theta))
    return theta

def icp_rotation(P, Q, max_iterations=500, tolerance=1e-6):
    """ICP algorithm implementation to get rotation angle"""
    # initialize the rotation matrix to identity
    R = np.eye(2)
    # create a KD tree for nearest neighbor search
    tree_Q = KDTree(Q)
    # iterate until convergence
    for i in range(max_iterations):
        # find the nearest neighbors of each point in P in Q
        distances, indices = tree_Q.query(P)
        # compute the centroid of each set of points
        centroid_P = np.mean(P, axis=0)
        centroid_Q = np.mean(Q[indices], axis=0)
        # compute the centered point sets
        P_centered = P - centroid_P
        Q_centered = Q[indices] - centroid_Q
        # compute the covariance matrix
        C = np.dot(np.transpose(Q_centered), P_centered)
        # compute the SVD of the covariance matrix
        U, _, V = np.linalg.svd(C)
        # compute the optimal rotation matrix
        R_new = np.dot(U, V)
        # update the rotation matrix
        R = np.dot(R_new, R)
        # update the point set P
        P = np.dot(P, R_new.T)
        # check for convergence
        if np.abs(np.trace(R_new) - 2) < tolerance:
            print(f'tolerace reached at iteration {i}')
            break
    # compute the rotation angle from the rotation matrix
    theta = np.degrees(np.arctan2(R[1, 0], R[0, 0]))
    return theta

def cc_rotation(points, *args):
    # Assume we have a grid of 2D points stored as a numpy array 'points', where each row represents a point
    # Create a template that is aligned with the grid (e.g., a 1D sine wave)
    template = np.sin(np.linspace(0, 2 * np.pi, len(points)))
    # Compute the cross-correlation of the grid with the template
    corr = correlate2d(points, template[:, np.newaxis], mode='same')
    # Find the peak of the cross-correlation
    peak = np.argmax(corr)
    # Compute the angle of the grid using the phase of the peak
    angle = np.angle(np.exp(1j * 2 * np.pi * peak / len(points)))
    return np.degrees(angle)

def hough_rotation(points):
    h, theta, d = hough_line(np.vstack([points[:, 1], points[:, 0]]))
    # Find the peaks in the Hough transform
    peaks = hough_line_peaks(h, theta, d)
    # Compute the angle of the dominant line
    angle = np.mean(peaks[1])
    return np.degrees(angle)

def PCA_rotation(points, *args):
    centered_points = points - np.mean(points, axis=0)
    # Compute the covariance matrix of the centered points
    cov = np.cov(centered_points.T)
    # Compute the eigenvectors and eigenvalues of the covariance matrix
    eigenvalues, eigenvectors = np.linalg.eig(cov)
    # Identify the index of the principal component (i.e., the eigenvector with the largest eigenvalue)
    principal_component_index = np.argmax(eigenvalues)
    # Compute the angle of the principal component
    angle = np.arctan2(eigenvectors[principal_component_index, 1], eigenvectors[principal_component_index, 0])
    return np.degrees(angle)

def get_mesh_rotation(grid:AutoloaderGrid, level:Callable=hole_mesh, algo:Callable=PCA_rotation):
    # grid = AutoloaderGrid.objects.get(pk=grid_id)
    targets, mesh_spacing = level(grid)
    stage_coords = np.array([t.coords for t in targets])
    # stage_coords -= stage_coords[0]
    # init_mesh = create_basic_mesh(mesh_spacing,int(np.ceil(stage_coords.shape[0]**0.5)))
    rotation = algo(stage_coords)
    logger.debug(f'Calculated mesh rotation: {rotation}')
    return rotation

