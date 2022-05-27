from multiprocessing.sharedctypes import Value
from pathlib import PureWindowsPath
from typing import Any
from Smartscope.lib.Datatypes.microscope import MicroscopeInterface
import serialem as sem
import time
import logging
import math

from Smartscope.lib.file_manipulations import generate_fake_file

logger = logging.getLogger(__name__)


class SerialemInterface(MicroscopeInterface):

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

    def atlas(self, mag, c2, spotsize, tileX, tileY, file='', center_stage_x=0, center_stage_y=0):
        logger.debug(f'Atlas mag:{mag}, c2perc:{c2}, spotsize:{spotsize}, tileX:{tileX}, tileY:{tileY}')
        sem.TiltTo(0)
        sem.MoveStageTo(center_stage_x, center_stage_y)
        sem.SetLowDoseMode(0)
        sem.SetMag(int(mag))
        sem.SetPercentC2(float(c2))
        sem.SetSpotSize(int(spotsize))
        self.eucentricHeight()
        sem.OpenNewMontage(tileX, tileY, file)
        logger.info('Starting Atlas acquisition')
        sem.Montage()
        sem.CloseFile()
        sem.SetLowDoseMode(1)
        logger.info('Atlas acquisition finished')

    def square(self, stageX, stageY, stageZ, file=''):
        sem.SetLowDoseMode(1)
        logger.info(f'Starting Square acquisition of: {file}')
        logger.debug(f'Moving stage to: X={stageX}, Y={stageY}, Z={stageZ}')
        time.sleep(0.2)
        sem.MoveStageTo(stageX, stageY, stageZ)
        self.eucentricHeight()
        self.checkDewars()
        self.checkPump()
        sem.MoveStageTo(stageX, stageY)
        time.sleep(0.2)
        sem.Search()
        sem.OpenNewFile(file)
        sem.Save()
        sem.CloseFile()
        logger.info('Square acquisition finished')

    def align(self):
        sem.View()
        sem.CropCenterToSize('A', 1700, 1700)
        sem.AlignTo('T')
        return sem.ReportAlignShift()

    def lowmagHole(self, stageX, stageY, stageZ, tiltAngle, file='', is_negativestain=False, aliThreshold=500):

        sem.TiltTo(tiltAngle)
        sem.ReadOtherFile(0, 'T', 'reference/holeref.mrc')  # Will need to change in the future for more flexibility
        sem.AllowFileOverwrite(1)
        sem.SetImageShift(0, 0)
        sem.MoveStageTo(stageX, stageY, stageZ)
        time.sleep(0.2)
        if not is_negativestain:
            aligned = self.align()
            holeshift = math.sqrt(aligned[4]**2 + aligned[5]**2)
            if holeshift > aliThreshold:
                if tiltAngle == 0:
                    sem.ResetImageShift()
                else:
                    iShift = sem.ReportImageShift()
                    sem.MoveStage(iShift[4], iShift[5] * math.cos(math.radians(tiltAngle)))
                    time.sleep(0.2)
                aligned = self.align()
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

    def highmag(self, isX, isY, tiltAngle, file='', frames=True):

        sem.ImageShiftByMicrons(isX - self.state.imageShiftX, isY - self.state.imageShiftY, 0)
        self.state.imageShiftX = isX
        self.state.imageShiftY = isY
        sem.SetDefocus(self.state.currentDefocus - isY * math.sin(math.radians(tiltAngle)))
        # checkDewars()
        # checkPump()
        if not frames:
            sem.EarlyReturnNextShot(-1)
            sem.Preview()
            sem.OpenNewFile(file)
            sem.Save()
            sem.CloseFile()
            return None

        sem.EarlyReturnNextShot(0)
        sem.Preview()  # Seems possible to change this to Record in 4.0, needs testing
        frames = sem.ReportLastFrameFile()
        if isinstance(frames, tuple):  # Workaround since the output of the ReportFrame command changed in 4.0, need to test ans simplify
            frames = frames[0]
        logger.debug(f"Frames: {frames},")
        return frames.split('\\')[-1]

    def connect(self, directory: str):
        logger.debug(f'{self.ip}:{self.port}')
        sem.ConnectToSEM(self.port, self.ip)
        sem.SetDirectory(directory)
        sem.ClearPersistentVars()
        sem.AllowFileOverwrite(1)

    def setup(self, saveframes, zerolossDelay):
        if saveframes:
            logger.info('Saving frames enabled')
            sem.SetDoseFracParams('P', 1, 1, 0)
            movies_directory = PureWindowsPath(self.directory, 'movies').as_posix().replace('/', '\\')
            logger.info(f'Saving frames to {movies_directory}')
            sem.SetFolderForFrames(movies_directory)
            # sem.EarlyReturnNextShot(0)
        else:
            logger.info('Saving frames disabled')
            sem.SetDoseFracParams('P', 1, 0, 1)
            # sem.EarlyReturnNextShot(-1)

        if self.energyfilter and zerolossDelay > 0:
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
        sem.SetColumnOrGunValve(1)


class FakeScopeInterface(MicroscopeInterface):

    # generate_fake_file: Any = None

    # def __post_init__(self):
    #     self.generate_fake_file = partial(generate_fake_file, destination_dir=self.scope_path)

    def checkDewars(self, wait=30) -> None:
        pass

    def checkPump(self, wait=30):
        pass

    def eucentricHeight(self, tiltTo=10, increments=-5) -> float:
        pass

    def atlas(self, mag, c2, spotsize, tileX, tileY, file='', center_stage_x=0, center_stage_y=0):
        generate_fake_file(file, 'atlas', destination_dir=self.scope_path)

    def square(self, stageX, stageY, stageZ, file=''):
        generate_fake_file(file, 'square', destination_dir=self.scope_path)

    def align():
        pass

    def lowmagHole(self, stageX, stageY, stageZ, tiltAngle, file='', is_negativestain=False, aliThreshold=500):
        generate_fake_file(file, 'lowmagHole', destination_dir=self.scope_path)

    def focusDrift(self, def1, def2, step, drifTarget):
        pass

    def highmag(self, isX, isY, tiltAngle, file='', frames=True):
        generate_fake_file(file, 'highmag', destination_dir=self.scope_path)

    def connect(self, directory: str):
        logger.info('Connecting to fake scope.')

    def setup(self, saveframes, zerolossDelay):
        pass

    def disconnect(self, close_valves=True):
        logger.info('Disconnecting from fake scope.')

    def loadGrid(self, position):
        pass
