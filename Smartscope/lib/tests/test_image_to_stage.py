import pytest
from pathlib import Path
from ..image.montage import Montage
from ..image.targets import Targets

def test_convert_coordinates_from_vector():
    montage_file = Path('/mnt/testfiles/square/1D1-1_2_square106.mrc')
    montage = Montage(name=montage_file.stem)
    montage.raw = montage_file
    montage.load_or_process()
    target = [1335,2653]
    targets = Targets.create_targets_from_center([target], montage)
    print(targets[0].stage_coords)