# import mrcfile
from ..Finders.calc_angle_spacing import calc_angle_spacing
from ..Finders.basic_finders import find_targets_binary
from ..image.montage import Montage
from Smartscope.core.grid.diagnostics import generate_diagnostic_figure
# import imutils

# def test_calc_angle_spacing():
#     montage = mrcfile.open('/mnt/testfiles/square/KS12_3_9_square12.mrc')
#     image= montage.data
#     # image = imutils.resize(image, width=2048)
#     orientation, spacing, _, ratio = calc_angle_spacing(image)
#     print(orientation, 1/spacing/ratio)


def test_find_targets_binary():
    montage = Montage(
        name='KS12_3_9_square12',
        working_dir='/mnt/testfiles/hole'
    )
    montage.raw = '/mnt/testfiles/hole/KS12_3_10_square60_hole9.mrc'
    montage.load_or_process()
    targets, _, _ = find_targets_binary(montage.image, minsize=4000, maxsize=500000)
    print(targets)
    print(len(targets))
    

    