from pathlib import PureWindowsPath, Path
from typing import Callable, Tuple, Optional
from abc import ABC
import serialem as sem
import time
import logging
import math
import numpy as np
from .microscope import CartridgeLoadingError
from .microscope_interface import MicroscopeInterface, MicroscopeLogger
from Smartscope.lib.Finders.basic_finders import find_square

logger = logging.getLogger(__name__)


class SerialEMLogger(MicroscopeLogger):

    def info(self, message:str):
        msg = self._create_message(message, self.prefix, self.info_prefix)
        logger.info(msg)
        sem.Echo(msg)
    
    def debug(self, message: str):
        msg = self._create_message(message, self.prefix, self.debug_prefix)
        logger.debug(msg)
        sem.Echo(msg)

class SerialemInterface(MicroscopeInterface):
    logger = SerialEMLogger()

    def eucentricHeight(self, tilt_to:int=10, increments:int=-5, max_movement:int=200):
        self.logger.info(f'Doing eucentric height')
        offsetZ = 51
        iteration = 0
        while abs(offsetZ) > 50 and iteration != 3:
            iteration += 1
            self.logger.info(f'Staring iteration {iteration}')
            alignments = []
            stageZ = sem.ReportStageXYZ()[2]
            sem.TiltTo(tilt_to)
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

            # self.logger.debug(', '.join(alignments))
            offsetZ = sum(alignments) / (len(alignments) * 1000)
            totalZ = stageZ + offsetZ
            if abs(totalZ) < max_movement:
                self.logger.info(f'Moving by {offsetZ} um')

                sem.MoveStage(0, 0, offsetZ)
                time.sleep(0.2)
            else:
                self.logger.info('Eucentric alignement would send the stage too far, stopping Eucentricity.')
                break

    def eucentricity(self):
        sem.GoToLowDoseArea('V')
        sem.Eucentricity(1)
    
    def eucentricity_by_focus(self):
        sem.GoToLowDoseArea('V')
        sem.Eucentricity(-1,-1)
    
    def call(self, script):
        sem.Call(script)

    def call_function(self, function:str, *args):
        str_args = [str(arg) for arg in args]
        sem.CallFunction(f"{function} {' '.join(str_args)}")
    
    def get_image_settings(self, magSet:str='V'):
        return sem.ReportCurrentPixelSize(magSet)
    
    def report_stage(self):
        return sem.ReportStageXYZ()
    
    def set_atlas_optics(self):
        self.logger.info('Setting atlas optics')
        self.logger.debug('Deactivating low dose mode')
        sem.SetLowDoseMode(0)
        self.logger.debug('Setting atlas mag')
        sem.SetMag(self.atlas_settings.mag)
        self.logger.debug('Setting spot size')
        sem.SetSpotSize(self.atlas_settings.spotSize)
        self.logger.debug('Setting C2 percent')
        sem.SetPercentC2(self.atlas_settings.c2)
        self.logger.info('Done setting atlas optics')
    
    def set_atlas_optics_delay(self, delay:int=1):
        self.logger.info(f'Setting atlas optics with a {delay} sec delay between each command.')
        self.logger.debug('Deactivating low dose mode')
        sem.SetLowDoseMode(0)
        time.sleep(delay)
        self.logger.debug('Setting atlas mag')
        sem.SetMag(self.atlas_settings.mag)
        time.sleep(delay)
        self.logger.debug('Setting spot size')
        sem.SetSpotSize(self.atlas_settings.spotSize)
        time.sleep(delay)
        self.logger.debug('Setting C2 percent')
        sem.SetPercentC2(self.atlas_settings.c2)
        time.sleep(delay)
        self.logger.info('Done setting atlas optics')

    def set_atlas_optics_imaging_state(self, state_name:str='Atlas'):
        self.logger.info(f'Setting atlas optics from the {state_name} imaging state')
        sem.GoToImagingState(state_name)
        self.logger.info('Done setting atlas optics')

    
    def reset_stage(self):
        self.logger.info(f'Resetting stage to center.')
        sem.TiltTo(0)
        sem.MoveStageTo(0,0,0)

    def remove_slit(self):
        if not self.detector.energyFilter:
            return
        if sem.ReportEnergyFilter()[2] == 1:
            self.logger.info('Removing slit.')
            sem.SetSlitIn(0)
        

    def atlas(self, size, file=''):
        sem.OpenNewMontage(size[0],size[1], file)
        self.checkDewars()
        self.checkPump()
        self.logger.info('Starting Atlas acquisition')
        sem.Montage()
        sem.CloseFile()
        self.logger.info('Atlas acquisition finished')

    def save_image(self, file:str):
        image_to_stage_matrix = sem.BufImageToStageMatrix('A', 1)
        image_to_stage_matrix = [str(x) for x in image_to_stage_matrix]
        sem.OpenNewFile(file)
        sem.Save()
        sem.AddToAutodoc('ImageToStageMatrix', ' '.join(image_to_stage_matrix))
        sem.WriteAutodoc()
        sem.CloseFile()

    def square(self, file=''):
        sem.SetLowDoseMode(1)
        sem.GoToLowDoseArea('S')
        self.checkDewars()
        self.checkPump()
        sem.Search()
        self.save_image(file)
        self.logger.info('Square acquisition finished')
    
    def buffer_to_numpy(self, buffer:str='A') -> Tuple[np.array, int, int, int, float, float]:
        sem.Delay(1)
        shape_x, shape_y, binning, exposure, pixel_size, _ = sem.ImageProperties(buffer)
        buffer = sem.bufferImage(buffer)
        return np.asarray(buffer), shape_x, shape_y, binning, exposure, pixel_size

    def numpy_to_buffer(self,image,buffer='T'):
        sem.PutImageInBuffer(image, buffer, *image.shape, 'A')
        

    def realign_to_square(self):
        self.tiltTo(0)
        while True:
            self.logger.info('Running square realignment')
            sem.Search()
            square, shape_x, shape_y, _, _, _ = self.buffer_to_numpy()
            _, square_center, _ = find_square(square)
            im_center = (square.shape[1] // 2, square.shape[0] // 2)
            diff = square_center - np.array(im_center)
            self.logger.info(f'Found square center: {square_center}. Image-shifting by {diff} pixels')
            sem.ImageShiftByPixels(int(diff[0]), -int(diff[1]))
            sem.ResetImageShift()
            if max(diff) < max(square.shape) // 4:
                self.logger.info('Done.')
                sem.Search()
                break
            self.logger.info('Iterating.')
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

    def moveStage(self,stage_x,stage_y,stage_z=None):
        sem.SetImageShift(0, 0)
        
        args = [stage_x, stage_y]
        if stage_z is not None:
            args.append(stage_z)
        self.logger.info(f'Moving stage to {args}.')
        sem.MoveStageTo(*args)
        self.state.setStage(*args)
    
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
        self.save_image(file)

    def autofocus(self, def1, def2, step):
        self.rollDefocus(def1, def2, step)
        sem.SetTargetDefocus(self.state.defocusTarget)
        sem.AutoFocus()
        self.state.currentDefocus = sem.ReportDefocus()
        self.state.set_last_autofocus_position()

    def wait_drift(self, drifTarget):
        if drifTarget > 0:
            sem.DriftWaitTask(drifTarget, 'A', 300, 10, -1, 'T', 1)

    def connect(self):
        logger.info(
            f"""
            Initiating connection to SerialEM at: {self.microscope.ip}:{self.microscope.port}
            If no more messages show up after this one and the External Control notification 
            is not showing up on the SerialEM interface, there is a problem.
            The best way to solve it is generally by closing and restarting SerialEM.
            """
        )
        sem.ConnectToSEM(self.microscope.port, self.microscope.ip)
        sem.SetDirectory(self.microscope.directory)
        sem.ClearPersistentVars()
        sem.AllowFileOverwrite(1)

    def setup(self, saveframes:bool, grid_dir:str='', framesName=None):
        if saveframes:
            self.logger.info('Saving frames enabled')
            sem.SetDoseFracParams('P', 1, 1, 0)
            movies_directory = PureWindowsPath(self.detector.framesDir, grid_dir).as_posix().replace('/', '\\')
            self.logger.info(f'SerialEM will be saving frames to {movies_directory}')
            sem.SetFolderForFrames(movies_directory)
            if framesName is not None:
                sem.SetFrameBaseName(0, 1, 0, framesName)
        else:
            self.logger.info('Saving frames disabled')
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
        
        self.logger.info("Closing Valves and disconnecting from SerialEM")
        if close_valves:
            try:
                sem.SetColumnOrGunValve(0)
            except:
                logger.warning("Could not close the column valves, still disconnecting from SerialEM")
        sem.Exit(1)

    def loadGrid(self, position):
        if self.microscope.loaderSize > 1:
            slot_status = sem.ReportSlotStatus(position)

            #This was added to support the new 4.1 2023-02-27 version 
            # that reports the name of the grid along with the position
            if isinstance(slot_status,tuple):
                slot_status = slot_status[0]
            
            if slot_status == -1:
                raise ValueError(f'SerialEM return an error when reading slot {position} of the autoloader.')
            if slot_status == 1:
                self.logger.info(f'Autoloader position is occupied')
                self.logger.info(f'Loading grid {position}')
                sem.Delay(5)
                sem.SetColumnOrGunValve(0)
                sem.LoadCartridge(position)
            self.logger.info(f'Grid {position} is loaded')
            sem.Delay(5)
            slot_status = sem.ReportSlotStatus(position)
            #This was added to support the new 4.1 2023-02-27 version 
            # that reports the name of the grid along with the position
            if isinstance(slot_status,tuple):
                slot_status = slot_status[0]
            if  slot_status != 0:
                raise CartridgeLoadingError('Cartridge did not load properly. Stopping')
        sem.SetColumnOrGunValve(1)

    def reset_image_shift(self):
        return sem.ResetImageShift()
    
    def reset_image_shift_values(self, afis:bool=False):
        self.state.reset_image_shift_values()
        self.state.preAFISimageShiftX, self.state.preAFISimageShiftY = sem.ReportImageShift()[:2]
        if afis:
            sem.SaveBeamTilt()
    
    def reset_AFIS_image_shift(self, afis:bool=False):
        sem.SetImageShift(self.state.preAFISimageShiftX, self.state.preAFISimageShiftY, 1, int(afis))
        if afis:
            sem.RestoreBeamTilt()

    def image_shift_by_microns(self,isX,isY,tiltAngle, afis:bool=False):
        sem.GoToLowDoseArea('Record')
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
            if isinstance(frames, tuple):  
                # Workaround since the output of the ReportFrame 
                # command changed in 4.0, need to test ans simplify
                frames = frames[0]
            self.logger.debug(f"Frames: {frames},")
            return frames.split('\\')[-1]
        
    def get_property(self, property_name:str):
        return sem.ReportProperty(property_name)
    

    def report_aperture_size(self, aperture:int):
        aperture_size = self.state.get_aperture_state(aperture)
        if not aperture_size is None:
            return aperture_size
        aperture_size = int(sem.ReportApertureSize(aperture))
        self.state.set_aperature_state(aperture, aperture_size)
        return aperture_size
           
    def remove_aperture(self,aperture:int, wait:int=10):
        inital_aperture_size = self.report_aperture_size(aperture)
        if inital_aperture_size == 0:
            self.logger.info( f'Aperture {aperture} already out.')
            return
        self.logger.info( f'Removing aperture {aperture} and waiting {wait}s.')
        sem.RemoveAperture(aperture)
        self.state.set_aperature_state(aperture, 0)
        time.sleep(wait)
        
    def insert_aperture(self, aperture:int, aperture_size:int, wait:int=10):
        if self.report_aperture_size(aperture) == aperture_size:
            self.logger.info( f'Aperture {aperture} already at {aperture_size}.')
            return
        self.logger.info( f'Inserting/Changing aperture {aperture} to {aperture_size} and waiting {wait}s.')
        sem.SetApertureSize(aperture, aperture_size)
        time.sleep(wait)
        self.state.set_aperature_state(aperture, aperture_size)

    def set_apertures_for_highmag(self, highmag_aperture_size:int, objective_aperture_size:int):
        if not self.microscope.apertureControl:
            return
        self.insert_aperture(self.apertures.OBJECTIVE, objective_aperture_size)
        self.insert_aperture(self.apertures.CONDENSER, highmag_aperture_size)

    def set_apertures_for_lowmag(self):
        if not self.microscope.apertureControl:
            return
        self.remove_aperture(self.apertures.OBJECTIVE)
        if self.atlas_settings.atlas_c2_aperture == 0:
            self.remove_aperture(self.apertures.CONDENSER)
            return
        self.insert_aperture(self.apertures.CONDENSER, self.atlas_settings.atlas_c2_aperture)

    def autofocus_after_distance(self, def1, def2, step, distance):
        last_autofocus_distance = self.state.get_last_autofocus_distance()
        if last_autofocus_distance > distance:
            self.logger.info(f'Last autofocus distance was {last_autofocus_distance} um (Threshold {distance} um), running autofocus')
            return self.autofocus(def1, def2, step)
        self.logger.debug(f'Last autofocus distance was {last_autofocus_distance} um (Threshold {distance} um), skipping autofocus.')
        defocus_target = self.state.defocusTarget
        current_defocus = self.state.currentDefocus
        new_defocus_target = self.rollDefocus(def1, def2, step)
        defocus_change = new_defocus_target - defocus_target
        self.logger.debug(f'Last defocus target: {defocus_target}. New defocus target: {defocus_target}. Change: {defocus_change}')
        sem.SetTargetDefocus(new_defocus_target)
        self.state.currentDefocus += defocus_change
        self.logger.debug(f'Current defocus: {current_defocus}. New current defocus: {self.state.currentDefocus}')
        if defocus_change != 0:
            sem.ChangeFocus(defocus_change)
            return

