from pathlib import PureWindowsPath
from typing import Callable, Tuple
import serialem as sem
import mrcfile
import time
import logging
import math
import os
import numpy as np
from Smartscope.lib.Datatypes.microscope import MicroscopeInterface, CartridgeLoadingError
from Smartscope.lib.Finders.basic_finders import find_square
from Smartscope.lib.file_manipulations import generate_fake_file, select_random_fake_file
from Smartscope.lib.image_manipulations import export_as_png

logger = logging.getLogger(__name__)

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

    def eucentricity(self):
        sem.GoToLowDoseArea('V')
        sem.Eucentricity(1)
    
    def get_image_settings(self, magSet:str='V'):
        return sem.ReportCurrentPixelSize(magSet)
    
    def report_stage(self):
        return sem.ReportStageXYZ()
    
    def set_atlas_optics(self):
        logger.info('Setting atlas optics')
        sem.SetLowDoseMode(0)
        sem.SetMag(self.atlasSettings.mag)
        sem.SetPercentC2(self.atlasSettings.c2)
        sem.SetSpotSize(self.atlasSettings.spotSize)

    def atlas(self, size, file=''):
        sem.TiltTo(0)
        sem.MoveStageTo(0,0)
        if self.detector.energyFilter:
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

    def square(self, file=''):
        sem.SetLowDoseMode(1)
        sem.GoToLowDoseArea('S')
        self.checkDewars()
        self.checkPump()
        sem.Search()
        sem.OpenNewFile(file)
        sem.Save()
        sem.CloseFile()
        logger.info('Square acquisition finished')
    
    def buffer_to_numpy(self, buffer:str='A') -> Tuple[np.array, int, int, int, float, float]:
        shape_x, shape_y, binning, exposure, pixel_size, _ = sem.ImageProperties(buffer)
        return np.asarray(sem.bufferImage(buffer)), shape_x, shape_y, binning, exposure, pixel_size

    def numpy_to_buffer(self,image,buffer='T'):
        sem.PutImageInBuffer(image, buffer, *image.shape, 'A')
        

    def realign_to_square(self):
        self.tiltTo(0)
        while True:
            logger.info('Running square realignment')
            sem.Search()
            square, shape_x, shape_y, _, _, _ = self.buffer_to_numpy()
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

    def align_to_hole_ref(self):
        sem.View()
        sem.CropCenterToSize('A', self.hole_crop_size, self.hole_crop_size)
        sem.AlignTo('T')
        return sem.ReportAlignShift()[5:]
    
    def align_to_coord(self, coord):
        sem.ImageShiftByPixels(coord[0], coord[1])
        sem.ResetImageShift()
        return sem.ReportStageXYZ()
    
    def setFocusPosition(self, distance, angle):
        sem.SetAxisPosition('F', distance, angle)
        self.focus_position_set = True

    def moveStage(self,stage_x,stage_y,stage_z):
        sem.SetImageShift(0, 0)
        sem.MoveStageTo(stage_x,stage_y,stage_z)
        self.state.setStage(stage_x,stage_y,stage_z)
    
    def get_conversion_matrix(self, magIndex=0):
        return sem.CameraToSpecimenMatrix(magIndex)

    def load_hole_ref(self):
        sem.ReadOtherFile(0, 'T', 'reference/holeref.mrc')
        shape_x, _, _, _, _, _ = sem.ImageProperties('T')
        self.hole_crop_size = int(shape_x)
        self.has_hole_ref = True

    def acquire_medium_mag(self):
        sem.GoToLowDoseArea('V')
        time.sleep(1)
        self.checkDewars()
        self.checkPump()
        sem.View()

    def tiltTo(self,tiltAngle):
        if self.state.tiltAngle == tiltAngle:
            return
        sem.TiltTo(tiltAngle)
        self.state.tiltAngle = tiltAngle

    def medium_mag_hole(self, file=''):
        sem.AllowFileOverwrite(1)
        self.acquire_medium_mag()
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

    def setup(self, saveframes, framesName=None):
        if saveframes:
            logger.info('Saving frames enabled')
            sem.SetDoseFracParams('P', 1, 1, 0)
            movies_directory = PureWindowsPath(self.detector.framesDir).as_posix().replace('/', '\\')
            logger.info(f'Saving frames to {movies_directory}')
            sem.SetFolderForFrames(movies_directory)
            if framesName is not None:
                sem.SetFrameBaseName(0, 1, 0, framesName)
        else:
            logger.info('Saving frames disabled')
            sem.SetDoseFracParams('P', 1, 0, 1)

        sem.KeepCameraSetChanges('P')
        sem.SetLowDoseMode(1)

    def refineZLP(self, zerolossDelay:float):
        if self.detector.energyFilter and zerolossDelay > 0:
            sem.RefineZLP(zerolossDelay * 60)
    
    def collectHardwareDark(self, harwareDarkDelay:int):
        if harwareDarkDelay > 0:
            sem.UpdateHWDarkRef(harwareDarkDelay)

    def disconnect(self, close_valves=True):
        
        logger.info("Closing Valves and disconnecting from SerialEM")
        if close_valves:
            try:
                sem.SetColumnOrGunValve(0)
            except:
                logger.warning("Could not close the column valves, still disconnecting from SerialEM")
        sem.Exit(1)

    def loadGrid(self, position):
        if self.microscope.loaderSize > 1:
            slot_status = sem.ReportSlotStatus(position)

            #This was added to support the new 4.1 2023-02-27 version that reports the name of the grid along with the position
            if isinstance(slot_status,tuple):
                slot_status = slot_status[0]
            
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
            slot_status = sem.ReportSlotStatus(position)
            #This was added to support the new 4.1 2023-02-27 version that reports the name of the grid along with the position
            if isinstance(slot_status,tuple):
                slot_status = slot_status[0]
            if  slot_status != 0:
                raise CartridgeLoadingError('Cartridge did not load properly. Stopping')
        sem.SetColumnOrGunValve(1)

    def reset_image_shift(self):
        return sem.ResetImageShift()
    
    def reset_image_shift_values(self):
        self.state.reset_image_shift_values()
        self.state.preAFISimageShiftX, self.state.preAFISimageShiftY = sem.ReportImageShift()[:2]
    
    def reset_AFIS_image_shift(self, afis:bool=False):
        sem.SetImageShift(self.state.preAFISimageShiftX, self.state.preAFISimageShiftY, 1, int(afis))

    def image_shift_by_microns(self,isX,isY,tiltAngle, afis:bool=False):
        sem.ImageShiftByMicrons(isX - self.state.imageShiftX, isY - self.state.imageShiftY, 1, int(afis))
        self.state.imageShiftX = isX
        self.state.imageShiftY = isY
        sem.SetDefocus(self.state.currentDefocus - isY * math.sin(math.radians(tiltAngle)))     

    def highmag(self, file='', frames=True, earlyReturn=False):

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
    def wrapper(*args, **kwargs):
        sem.RemoveAperture(0)
        function(*args, **kwargs)
        sem.ReInsertAperture(0)
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

    def set_atlas_optics(self):
        pass

    def checkDewars(self, wait=30) -> None:
        pass

    def checkPump(self, wait=30):
        pass

    def eucentricHeight(self, tiltTo=10, increments=-5) -> float:
        pass

    def eucentricity():
        pass

    def moveStage(self, stage_x, stage_y, stage_z):
        pass

    def realign_to_square(self):
        return super().realign_to_square()

    def atlas(self, size, file=''):
        generate_fake_file(file, 'atlas', destination_dir=self.microscope.scopePath)

    def square(self, file=''):
        generate_fake_file(file, 'square', sleeptime=15, destination_dir=self.microscope.scopePath)
        return 0, 0, 0

    def align():
        pass

    def image_shift_by_microns(self, isX, isY, tiltAngle):
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
        file = select_random_fake_file('lowmagHole')
        logger.debug(f'Using {file} to generate fake buffer')
        with mrcfile.open(file) as mrc:
            header = mrc.header
            img = mrc.data
        return img, header.nx, header.ny, 1, 1, header.cella.x/header.nx/10
    
    def numpy_to_buffer(sekf,image):
        export_as_png(image, output=os.path.join(os.getenv('TEMPDIR'),'mockNumpyToBuffer.png'),height=max([image.shape[0],1024]))

    def medium_mag_hole(self, file=''):
        generate_fake_file(file, 'lowmagHole', sleeptime=10, destination_dir=self.microscope.scopePath)

    def focusDrift(self, def1, def2, step, drifTarget):
        pass

    def tiltTo(self,tiltAngle):
        pass

    def highmag(self, file='', frames=True, earlyReturn=False):
        if not frames:
            generate_fake_file(file, 'highmag', sleeptime=7, destination_dir=self.microscope.scopePath)
            return
        frames = generate_fake_file(file, 'highmagframes', sleeptime=7, destination_dir=os.path.join(self.microscope.scopePath, 'movies'))
        return frames.split('\\')[-1]

    def connect(self):
        logger.info('Connecting to fake scope.')

    def setup(self, saveframes, framesName=None):
        pass

    def disconnect(self, close_valves=True):
        logger.info('Disconnecting from fake scope.')

    def loadGrid(self, position):
        pass
