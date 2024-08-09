import pytest
from pathlib import Path
from ..image.montage import Montage
from ..image.target import Target

def test_convert_coordinates_from_vector():
    montage_file = Path('/mnt/testfiles/square/1D1-1_2_square106.mrc')
    montage = Montage(name=montage_file.stem)
    montage.raw = montage_file
    montage.load_or_process()
    coords = [3000,3000]
    target = Target(coords, from_center=True)
    target.convert_image_coords_to_stage(montage, compare=True)