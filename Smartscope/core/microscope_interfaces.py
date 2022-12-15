from pathlib import PureWindowsPath
from typing import Callable
from Smartscope.lib.Datatypes.microscope import MicroscopeInterface
import serialem as sem
import time
import logging
import math
import numpy as np
from Smartscope.lib.Finders.basic_finders import find_square
from Smartscope.lib.image_manipulations import generate_hole_ref


from Smartscope.lib.file_manipulations import generate_fake_file

logger = logging.getLogger(__name__)


class CartridgeLoadingError(Exception):
    pass


class SerialemInterface(MicroscopeInterface):

    def eucentricHeight(self, tiltTo=10, increments=-5):
        logger.info(f'Doing eucentric height')
        offsetZ = 51
        iteration = 0
        while abs(offsetZ) > 50 and iteration != 3:
            iteration += 1
            logger.info(f'Staring iteration {iteration}')
            alignments = []
            stageZ = sem.ReportStageXYZ()[2]
            sem.TiltTo(tiltTo)
            currentAngle = int(sem.ReportTiltAngle())
            sem.Search()
            loop = 0
            while currentAngle > 0:
                loop += 1
                sem.TiltBy(increments)
                currentAngle = int(sem.ReportTiltAngle())
                sem.Search()
                sem.AlignTo('B', 1)
                alignments.append(sem.ReportAlignShift()[5] / math.sin(math.radians(abs(increments) * loop)))

            logger.debug(alignments)
            offsetZ = sum(alignments) / (len(alignments) * 1000)
            totalZ = stageZ + offsetZ
            if abs(totalZ) < 200:
                logger.info(f'Moving by {offsetZ} um')

                sem.MoveStage(0, 0, offsetZ)
                time.sleep(0.2)
            else:
                logger.info('Eucentric alignement would send the stage too far, stopping Eucentricity.')
                break
    
    def get_image_settings(self, magSet:str='V'):
        shapeX,shapeY,_,_,_,_ =sem.ReportCurrentPixelSize(magSet)
        pixel_size = sem.ReportCameraSetArea(magSet) / 1000
        return shapeX*pixel_size,shapeY*pixel_size
    
    def set_atlas_optics(self):
        logger.info('Setting atlas optics')
        sem.SetLowDoseMode(0)
        sem.SetMag(self.atlasSettings.mag)
        sem.SetPercentC2(self.atlasSettings.c2)
        sem.SetSpotSize(self.atlasSettings.spotSize)

    def atlas(self, size, file=''):
        sem.TiltTo(0)
        sem.MoveStageTo(0,0)
        if self.energyfilter:
            if sem.ReportEnergyFilter()[2] == 1:
                sem.SetSlitIn(0)
        self.eucentricHeight()
        sem.OpenNewMontage(size[0],size[1], file)
        self.checkDewars()
        self.checkPump()
        logger.info('Starting Atlas acquisition')
        sem.Montage()
        sem.CloseFile()
        logger.info('Atlas acquisition finished')
        sem.SetLowDoseMode(1)

    def square(self, stageX, stageY, stageZ, file=''):
        sem.SetLowDoseMode(1)
        sem.GoToLowDoseArea('S')
        logger.info(f'Starting Square acquisition of: {file}')
        logger.debug(f'Moving stage to: X={stageX}, Y={stageY}, Z={stageZ}')
        time.sleep(0.2)
        sem.MoveStageTo(stageX, stageY, stageZ)
        stageX, stageY, stageZ = self.realign_to_square()
        sem.GoToLowDoseArea('V')
        sem.Eucentricity(1)
        self.checkDewars()
        self.checkPump()
        sem.MoveStageTo(stageX, stageY)
        time.sleep(0.2)
        sem.Search()
        sem.OpenNewFile(file)
        sem.Save()
        sem.CloseFile()
        logger.info('Square acquisition finished')
        return stageX, stageY, stageZ

    def realign_to_square(self):
        while True:
            logger.info('Running square realignment')
            sem.Search()
            square = np.asarray(sem.bufferImage('A'))
            _, square_center, _ = find_square(square)
            im_center = (square.shape[1] // 2, square.shape[0] // 2)
            diff = square_center - np.array(im_center)
            logger.info(f'Found square center: {square_center}. Image-shifting by {diff} pixels')
            sem.ImageShiftByPixels(int(diff[0]), -int(diff[1]))
            sem.ResetImageShift()
            if max(diff) < max(square.shape) // 4:
                logger.info('Done.')
                sem.Search()
                break
            logger.info('Iterating.')
        return sem.ReportStageXYZ()

    def align(self):
        sem.View()
        sem.CropCenterToSize('A', self.hole_crop_size, self.hole_crop_size)
        sem.AlignTo('T')
        return sem.ReportAlignShift()
    
    def align_to_coord(self, coord):
        sem.ImageShiftByPixels(coord[0], coord[1])
        sem.ResetImageShift()
        return sem.ReportStageXYZ()

    
    def get_conversion_matrix(self, magIndex=0):
        return sem.CameraToSpecimenMatrix(magIndex)
    # def make_hole_ref(self, hole_size_in_um):

    #     # sem.View()
    #     # img = np.asarray(sem.bufferImage('A'))
    #     # dtype = img.dtype
    #     # shape_x, shape_y, _, _, pixel_size, _ = sem.ImageProperties('A')
    #     # logger.debug(f'\nImage dtype: {dtype}\nPixel size: {pixel_size}')
    #     # ref = generate_hole_ref(hole_size_in_um, pixel_size * 10, out_type=dtype)
    #     # self.hole_crop_size = int(min([shape_x, shape_y, ref.shape[0] * 1.5]))
    #     # sem.PutImageInBuffer(ref, 'T', ref.shape[0], ref.shape[1])
    #     sem.ReadOtherFile(0, 'T', 'reference/holeref.mrc')  # Will need to change in the future for more flexibility
    #     shape_x, _, _, _, _, _ = sem.ImageProperties('T')
    #     self.hole_crop_size = int(shape_x)
    #     self.has_hole_ref = True

    def lowmagHole(self, stageX, stageY, stageZ, tiltAngle, file=''):
        sem.GoToLowDoseArea('V')
        sem.TiltTo(tiltAngle)

        sem.AllowFileOverwrite(1)
        sem.SetImageShift(0, 0)
        sem.MoveStageTo(stageX, stageY, stageZ)
        time.sleep(0.2)
        
        self.checkDewars()
        self.checkPump()
        sem.View()
        sem.OpenNewFile(file)
        sem.Save()
        sem.CloseFile()

    def focusDrift(self, def1, def2, step, drifTarget):
        self.rollDefocus(def1, def2, step)
        sem.SetTargetDefocus(self.state.defocusTarget)
        sem.AutoFocus()
        self.state.currentDefocus = sem.ReportDefocus()
        if drifTarget > 0:
            sem.DriftWaitTask(drifTarget, 'A', 300, 10, -1, 'T', 1)

    def connect(self):
        logger.info(
            f'Initiating connection to SerialEM at: {self.microscope.ip}:{self.microscope.port}\n\t If no more messages show up after this one and the External Control notification is not showing up on the SerialEM interface, there is a problem. \n\t The best way to solve it is generally by closing and restarting SerialEM.')
        sem.ConnectToSEM(self.microscope.port, self.microscope.ip)
        sem.SetDirectory(self.microscope.directory)
        sem.ClearPersistentVars()
        sem.AllowFileOverwrite(1)

    def setup(self, saveframes, zerolossDelay, framesName=None):
        if saveframes:
            logger.info('Saving frames enabled')
            sem.SetDoseFracParams('P', 1, 1, 0)
            movies_directory = PureWindowsPath(self.frames_directory).as_posix().replace('/', '\\')
            logger.info(f'Saving frames to {movies_directory}')
            sem.SetFolderForFrames(movies_directory)
            if framesName is not None:
                sem.SetFrameBaseName(0, 1, 0, framesName)
        else:
            logger.info('Saving frames disabled')
            sem.SetDoseFracParams('P', 1, 0, 1)

        if self.detector.energyFilter and zerolossDelay > 0:
            sem.RefineZPL(zerolossDelay * 60, 1)
        sem.KeepCameraSetChanges('P')
        sem.SetLowDoseMode(1)

    def disconnect(self, close_valves=True):
        logger.info("Closing Valves and disconnecting from SerialEM")
        if close_valves:
            try:
                sem.SetColumnOrGunValve(0)
            except:
                logger.warning("Could not close the column valves, still disconnecting from SerialEM")
        sem.Exit(1)

    def loadGrid(self, position):
        if self.microscope.loader_size > 1:
            slot_status = sem.ReportSlotStatus(position)
            if slot_status == -1:
                raise ValueError(f'SerialEM return an error when reading slot {position} of the autoloader.')
            if slot_status == 1:
                logger.info(f'Autoloader position is occupied')
                logger.info(f'Loading grid {position}')
                sem.Delay(5)
                sem.SetColumnOrGunValve(0)
                sem.LoadCartridge(position)
            logger.info(f'Grid {position} is loaded')
            sem.Delay(5)
            if sem.ReportSlotStatus(position) != 0:
                raise CartridgeLoadingError('Cartridge did not load properly. Stopping')
        sem.SetColumnOrGunValve(1)

    def highmag(self, isX, isY, tiltAngle, file='', frames=True, earlyReturn=False):

        sem.ImageShiftByMicrons(isX - self.state.imageShiftX, isY - self.state.imageShiftY, 0)
        self.state.imageShiftX = isX
        self.state.imageShiftY = isY
        sem.SetDefocus(self.state.currentDefocus - isY * math.sin(math.radians(tiltAngle)))

        if not earlyReturn:
            sem.EarlyReturnNextShot(0)

        sem.Preview()
        if earlyReturn:
            sem.OpenNewFile(file)
            sem.Save()
            sem.CloseFile()

        if frames:
            frames = sem.ReportLastFrameFile()
            if isinstance(frames, tuple):  # Workaround since the output of the ReportFrame command changed in 4.0, need to test ans simplify
                frames = frames[0]
            logger.debug(f"Frames: {frames},")
            return frames.split('\\')[-1]


class TFSSerialemInterface(SerialemInterface):

    def checkDewars(self, wait=30):
        while True:
            if sem.AreDewarsFilling() == 0:
                return
            logger.info(f'LN2 is refilling, waiting {wait}s')
            time.sleep(wait)

    def checkPump(self, wait=30):
        while True:
            if sem.IsPVPRunning() == 0:
                return
            logger.info(f'Pump is Running, waiting {wait}s')
            time.sleep(wait)


def remove_condenser_aperture(function: Callable, *args, **kwargs):
    def wrapper():
        sem.RemoveAperture(0)
        function(*args, **kwargs)
        sem.ReinsertAperture(0)
    return wrapper


class JEOLSerialemInterface(SerialemInterface):

    def checkPump(self, wait=30):
        pass

    def checkDewars(self, wait=30):
        while True:
            if sem.AreDewarsFilling() == 0:
                return
            logger.info(f'LN2 is refilling, waiting {wait}s')
            time.sleep(wait)

    @remove_condenser_aperture
    def atlas(self, *args, **kwargs):
        super().atlas(*args,**kwargs)


class FakeScopeInterface(MicroscopeInterface):

    def checkDewars(self, wait=30) -> None:
        pass

    def checkPump(self, wait=30):
        pass

    def eucentricHeight(self, tiltTo=10, increments=-5) -> float:
        pass

    def atlas(self, size, file=''):
        generate_fake_file(file, 'atlas', destination_dir=self.microscope.scopePath)

    def square(self, stageX, stageY, stageZ, file=''):
        generate_fake_file(file, 'square', sleeptime=15, destination_dir=self.microscope.scopePath)
        return 0, 0, 0

    def align():
        pass

    def lowmagHole(self, stageX, stageY, stageZ, tiltAngle, hole_size_in_um, file='', is_negativestain=False, aliThreshold=500):
        generate_fake_file(file, 'lowmagHole', sleeptime=10, destination_dir=self.microscope.scopePath)

    def focusDrift(self, def1, def2, step, drifTarget):
        pass

    def highmag(self, isX, isY, tiltAngle, file='', frames=True, earlyReturn=False):
        generate_fake_file(file, 'highmag', sleeptime=7, destination_dir=self.microscope.scopePath)

    def connect(self):
        logger.info('Connecting to fake scope.')

    def setup(self, saveframes, zerolossDelay, framesName=None):
        pass

    def disconnect(self, close_valves=True):
        logger.info('Disconnecting from fake scope.')

    def loadGrid(self, position):
        pass
