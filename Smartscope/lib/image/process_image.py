
import numpy as np
from math import radians, cos
from scipy.spatial.distance import cdist

class ProcessImage:

    @staticmethod
    def closest_node(node, nodes, num=1):
        nodes = np.stack((nodes))
        cd = cdist(node, nodes)
        index = cd.argmin()
        dist = nodes[index] - node
        return index, dist

    @staticmethod
    def pixel_to_stage(dist, tile, tiltAngle=0):
        apix = tile.PixelSpacing / 10_000
        dist *= apix
        specimen_dist = ProcessImage.rotate_axis(dist,tile.RotationAngle)
        coords = tile.StagePosition + specimen_dist / \
            np.array([1, cos(radians(round(tiltAngle, 1)))])
        return np.around(coords, decimals=3)


