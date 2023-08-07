from commons import *
from Smartscope.lib.image.base_image import BaseImage

os.chdir(TESTS_DATA_DIR)
CURR_DIR = os.getcwd()
print(f'###{CURR_DIR}')

@ddt
class TestBaseImage(TestCase):

    # def setUp(self):
    #     self.c = BaseImage('')

    @data(
        ['abc', 'abc',],
    )
    @unpack
    def test_name(self, name, expect):
        c = BaseImage(name)
        assert c.name == expect

    @data(
        ['abc', 'abc',],
    )
    @unpack
    def test_directory(self, name, expect):
        c = BaseImage(name)
        assert c.directory.name == expect
        


    @data(
        ['abc', f'{CURR_DIR}/pngs/abc.png',],
    )
    @unpack
    def test_png(self, name, expect):
        c = BaseImage(name)
        assert c.png.resolve().as_posix() == expect

    @data(
        ['abc', f'{CURR_DIR}/raw/abc.mrc',],
    )
    @unpack
    def test_raw(self, name, expect):
        c = BaseImage(name)
        assert c.raw.resolve().as_posix() == expect


    @data(
        ['abc', None,],
        [
            'Htr1_1_square24_hole172',
            Path('raw/Htr1_1_square24_hole172.mrc.mdoc'),
        ],
    )
    @unpack
    def test_mdoc(self, name, expect):
        c = BaseImage(name)
        assert c.mdoc == expect


    @data(
        [
            'abc',
            f'{CURR_DIR}/abc/abc.mrc',
            None,
        ],
        [
            'Htr1_1_square24_hole172',
            f'{CURR_DIR}/Htr1_1_square24_hole172/Htr1_1_square24_hole172.mrc',
            (3838, 3708)
        ]
    )
    @unpack
    def test_image(self, name, image_path, image):
        c = BaseImage(name)
        assert c.image_path.resolve().as_posix() == image_path
        if image is None:
            with self.assertRaises(Exception) as e:
                assert c.image == image
            with self.assertRaises(Exception) as e:
                c.read_image()
            assert 'File not found.' in e.exception.__doc__
        else:
            assert c.image_path.name == f"{name}.mrc"
            c.read_image()
            assert c.image.shape == image


    @data(
        [
            'Htr1_1_square24_hole172',
            (3838, 3708),
            [1854, 1919],
        ]
    )
    @unpack
    def test_image_params(self, name, shape, center):
        c = BaseImage(name)
        c.read_image()
        c.set_shape_from_image()

        assert (c._shape_x, c._shape_y) == shape
        assert list(c.center) == center



    @data(
        ['abc', 'abc_metadata.pkl', False,
            None, None, None],
        [
            'Htr1_1_square24_hole172',
            'Htr1_1_square24_hole172_metadata.pkl',
            True,
            float(-88.1),
            -7.3203,
            34.17
        ]
    )
    @unpack
    def test_metadata(self, name, metadata_file, file_exists, \
            roation_angle, stage_z, pixel_size):
        c = BaseImage(name)
        assert c.metadataFile.name == metadata_file 

        res = c.check_metadata()
        assert res == file_exists
        if res:
            assert float(c.rotation_angle) == roation_angle
            assert c.stage_z == stage_z
            assert c.pixel_size == pixel_size


