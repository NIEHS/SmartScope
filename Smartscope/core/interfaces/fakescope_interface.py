import mrcfile
import time
import logging
import os
from .microscope_interface import MicroscopeInterface
from Smartscope.lib.file_manipulations.fake import Fake
from Smartscope.lib.image_manipulations import export_as_png


logger = logging.getLogger(__name__)

class FakeScopeInterface(MicroscopeInterface):

    def set_atlas_optics(self):
        logger.info(f'Setting atlas optics')
        logger.info('Done setting atlas optics')

    def set_atlas_optics_delay(self, delay:int=1):
        logger.info(f'Setting atlas optics with a {delay} sec delay between each command.')
        logger.info('Done setting atlas optics')

    def set_atlas_optics_imaging_state(self, state_name:str='Atlas'):
        logger.info(f'Setting atlas optics from the {state_name} imaging state')
        logger.info('Done setting atlas optics')

    def checkDewars(self, wait=30) -> None:
        pass

    def checkPump(self, wait=30):
        pass

    def eucentricHeight(self, tiltTo=10, increments=-5) -> float:
        pass

    def eucentricity(self):
        pass

    def moveStage(self, stage_x, stage_y, stage_z):
        pass

    def realign_to_square(self):
        return super().realign_to_square()

    def atlas(self, size, file=''):
        Fake.generate_fake_file(
            file,
            'atlas',
            destination_dir=self.microscope.scopePath
        )

    def square(self, file=''):
        Fake.generate_fake_file(
            file,
            'square',
            sleeptime=15,
            destination_dir=self.microscope.scopePath
        )
        return 0, 0, 0

    def align():
        pass

    def image_shift_by_microns(self, isX, isY, tiltAngle, afis=False):
        return super().image_shift_by_microns(isX, isY, tiltAngle)

    def reset_image_shift(self):
        return super().reset_image_shift()

    def align_to_hole_ref(self):
        return super().align_to_hole_ref()

    def acquire_medium_mag(self,):
        return super().acquire_medium_mag()

    def align_to_coord(self, coord):
        return super().align_to_coord(coord)
    
    def get_image_settings(self, *args, **kwargs):
        return super().get_image_settings(*args, **kwargs)
    
    def load_hole_ref(self):
        return super().load_hole_ref()
    
    def report_stage(self):
        return super().report_stage()
    
    def setFocusPosition(self, distance, angle):
        # sem.SetAxisPosition('F', distance, angle)
        self.focus_position_set = True
    
    def buffer_to_numpy(self):
        '''
        command: highmag_processing <grid_id>
        '''
        file = Fake.select_random_fake_file('lowmagHole')
        logger.debug(f'Using {file} to generate fake buffer')
        with mrcfile.open(file) as mrc:
            header = mrc.header
            img = mrc.data
        return img, header.nx, header.ny, 1, 1, header.cella.x/header.nx/10
    
    def numpy_to_buffer(sekf,image):
        export_as_png(image, output=os.path.join(os.getenv('TEMPDIR'),'mockNumpyToBuffer.png'),height=max([image.shape[0],1024]))

    def medium_mag_hole(self, file=''):
        Fake.generate_fake_file(
            file,
            'lowmagHole',
            sleeptime=10,
            destination_dir=self.microscope.scopePath
        )

    def focusDrift(self, def1, def2, step, drifTarget):
        pass

    def tiltTo(self,tiltAngle):
        pass

    def highmag(self, file='', frames=True, earlyReturn=False):
        if not frames:
            Fake.generate_fake_file(
                file,
                'highmag',
                sleeptime=7,
                destination_dir=self.microscope.scopePath
            )
            return
        movies = os.path.join(self.microscope.scopePath, 'movies')
        logger.info(f"High resolution movies are stored at {movies} in fake mode")
        frames = Fake.generate_fake_file(
            file,
            'highmagframes',
            sleeptime=7,
            destination_dir=movies
        )
        return frames.split('\\')[-1]

    def connect(self):
        logger.info('Connecting to fake scope.')

    def setup(self, saveframes, framesName=None):
        pass

    def disconnect(self, close_valves=True):
        logger.info('Disconnecting from fake scope.')

    def loadGrid(self, position):
        pass
