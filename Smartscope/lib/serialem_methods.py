import serialem as sem
import time
import math
import os
import logging
import numpy as np
from Smartscope.lib.file_manipulations import generate_fake_file

proclog = logging.getLogger('processing')
mainlog = logging.getLogger('autoscreen')


def SerialEM(func):
    connected = eval(os.getenv('SEM_PYTHON'))
    testmode = eval(os.getenv('NO_TEM_TESTMODE'))

    def wrapper(*args, **kwargs):
        if connected:
            return func(*args, **kwargs)
        elif testmode:
            return fake_scope(func, *args, **kwargs)
        return

    return wrapper


def fake_scope(func, *args, **kwargs):
    mainlog.info(f'SerialEM disconnected, running {func.__name__} ({args}, {kwargs}) in test mode')
    file = kwargs.pop('file', '')
    if file != '':
        return generate_fake_file(file, func.__name__, **kwargs)

    mainlog.debug(f'No file specified')


@SerialEM
def checkDewars(wait=30):
    while True:
        if sem.AreDewarsFilling() == 1:
            mainlog.info(f'LN2 is refilling, waiting {wait}s')
            time.sleep(wait)
        else:
            return


@SerialEM
def checkPump(wait=30):
    while True:
        if sem.IsPVPRunning() == 1:
            mainlog.info(f'Pump is Running, waiting {wait}s')
            time.sleep(wait)
        else:
            return


@SerialEM
def rollDefocus(def1, def2, step):
    mindef = max([def1, def2])
    maxdef = min([def1, def2])
    defocusTarget = round(sem.ReportTargetDefocus() - abs(step), 2)
    if defocusTarget < maxdef or defocusTarget > mindef:
        defocusTarget = mindef

    sem.SetTargetDefocus(defocusTarget)
    return defocusTarget


@SerialEM
def eucentricHeight(tiltTo=10, increments=-5):
    mainlog.info(f'Doing eucentric height')
    offsetZ = 51
    iteration = 0
    while abs(offsetZ) > 50 and iteration != 3:
        iteration += 1
        mainlog.info(f'Staring iteration {iteration}')
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

        mainlog.debug(alignments)
        offsetZ = sum(alignments) / (len(alignments) * 1000)
        totalZ = stageZ + offsetZ
        if abs(totalZ) < 200:
            mainlog.info(f'Moving by {offsetZ} um')

            sem.MoveStage(0, 0, offsetZ)
            time.sleep(0.2)
        else:
            mainlog.info('Eucentric alignement would send the stage too far, stopping Eucentricity.')
            break


@SerialEM
def atlas(mag, c2, spotsize, tileX, tileY, file='', center_stage_x=0, center_stage_y=0):
    mainlog.debug(f'Atlas mag:{mag}, c2perc:{c2}, spotsize:{spotsize}, tileX:{tileX}, tileY:{tileY}')
    sem.TiltTo(0)
    sem.MoveStageTo(center_stage_x, center_stage_y)
    sem.SetLowDoseMode(0)
    sem.SetMag(int(mag))
    sem.SetPercentC2(float(c2))
    sem.SetSpotSize(int(spotsize))
    eucentricHeight()
    sem.OpenNewMontage(tileX, tileY, file)
    mainlog.info('Starting Atlas acquisition')
    sem.Montage()
    sem.CloseFile()
    sem.SetLowDoseMode(1)
    mainlog.info('Atlas acquisition finished')


@SerialEM
def square(stageX, stageY, stageZ, file=''):
    sem.SetLowDoseMode(1)
    mainlog.info(f'Starting Square acquisition of: {file}')
    mainlog.debug(f'Moving stage to: X={stageX}, Y={stageY}, Z={stageZ}')
    time.sleep(0.2)
    sem.MoveStageTo(stageX, stageY, stageZ)
    eucentricHeight()
    checkDewars()
    checkPump()
    sem.MoveStageTo(stageX, stageY)
    time.sleep(0.2)
    sem.Search()
    sem.OpenNewFile(file)
    sem.Save()
    sem.CloseFile()
    mainlog.info('Square acquisition finished')


@SerialEM
def lowmagHole(stageX, stageY, stageZ, tiltAngle, file='', is_negativestain=False, aliThreshold=500):

    def align():
        sem.View()
        sem.CropCenterToSize('A', 1700, 1700)
        sem.AlignTo('T')
        return sem.ReportAlignShift()

    sem.TiltTo(tiltAngle)
    sem.ReadOtherFile(0, 'T', 'reference/holeref.mrc')  # Will need to change in the future for more flexibility
    sem.AllowFileOverwrite(1)
    sem.SetImageShift(0, 0)
    sem.MoveStageTo(stageX, stageY, stageZ)
    time.sleep(0.2)
    if not is_negativestain:
        aligned = align()
        holeshift = math.sqrt(aligned[4]**2 + aligned[5]**2)
        if holeshift > aliThreshold:
            if tiltAngle == 0:
                sem.ResetImageShift()
            else:
                iShift = sem.ReportImageShift()
                sem.MoveStage(iShift[4], iShift[5] * math.cos(math.radians(tiltAngle)))
                time.sleep(0.2)
            aligned = align()
    checkDewars()
    checkPump()
    sem.View()
    sem.OpenNewFile(file)
    sem.Save()
    sem.CloseFile()


@SerialEM
def focusDrift(def1, def2, step, drifTarget):
    rollDefocus(def1, def2, step)
    sem.AutoFocus()
    currentDefocus = sem.ReportDefocus()
    if drifTarget > 0:
        sem.DriftWaitTask(drifTarget, 'A', 300, 10, -1, 'T', 1)
    return currentDefocus


@SerialEM
def highmag(isXi, isYi, isX, isY, currentDefocus, tiltAngle, file='', frames=True):

    sem.ImageShiftByMicrons(isX - isXi, isY - isYi, 0)
    sem.SetDefocus(currentDefocus - isY * math.sin(math.radians(tiltAngle)))
    # checkDewars()
    # checkPump()
    if not frames:
        sem.EarlyReturnNextShot(-1)
        sem.Preview()
        sem.OpenNewFile(file)
        sem.Save()
        sem.CloseFile()
        frames = None
    else:
        sem.EarlyReturnNextShot(0)
        sem.Preview()
        frames = sem.ReportLastFrameFile()
        if isinstance(frames, tuple):
            frames = frames[0]
    mainlog.debug(f"Frames: {frames},")
    return isX, isY, frames.split('\\')[-1]


@SerialEM
def connect(ip: str, port: int, directory: str):
    mainlog.debug(f'{ip}:{port}')
    sem.ConnectToSEM(port, ip)
    sem.SetDirectory(directory)
    sem.ClearPersistentVars()
    sem.AllowFileOverwrite(1)


@SerialEM
def setup(saveframes, energyfilter, zerolossDelay):
    if saveframes:
        mainlog.info('Saving frames enabled')
        sem.SetDoseFracParams('P', 1, 1, 0)
        # sem.EarlyReturnNextShot(0)
    else:
        mainlog.info('Saving frames disabled')
        sem.SetDoseFracParams('P', 1, 0, 1)
        # sem.EarlyReturnNextShot(-1)

    if energyfilter and zerolossDelay > 0:
        sem.RefineZPL(zerolossDelay * 60, 1)
    sem.KeepCameraSetChanges('P')
    sem.SetLowDoseMode(1)


@SerialEM
def disconnect(close_valves=True):
    mainlog.info("Closing Valves and disconnecting from SerialEM")
    if close_valves:
        try:
            sem.SetColumnOrGunValve(0)
        except:
            mainlog.warning("Could not close the column valves, still disconnecting from SerialEM")
    sem.Exit(1)


@SerialEM
def loadGrid(position):

    if sem.ReportSlotStatus(position) == 1:
        mainlog.info(f'Loading grid {position}')
        sem.Delay(5)
        sem.SetColumnOrGunValve(0)
        sem.LoadCartridge(position)
    mainlog.info(f'Grid {position} is loaded')
    sem.Delay(5)
    sem.SetColumnOrGunValve(1)


if __name__ == "__main__":
    FORMAT = "[%(levelname)s] %(funcName)s, %(asctime)s: %(message)s"
    logging.basicConfig(format=FORMAT, datefmt="%Y-%m-%d %H:%M:%S", level=logging.DEBUG)
    try:
        disconnect(close_valves=False)
        mainlog.info('Starting')
        connect(os.getenv('SEM_IP'), int(os.getenv('SEM_PORT')), 'X:/auto_screening/')

        # sem.Search()
        # im = np.asarray(sem.bufferImage('A'))
        # sem.ImageMetadataToVar('A', 'meta')
        # meta = sem.GetVariable('meta')
        # mainlog.info(im.shape)
        # mainlog.info(meta)
        # import pickle
        # with open('/home/bouvettej2/imobj.pkl', 'wb') as f:
        #     pickle.dump([im, meta], f)

    except Exception as e:
        mainlog.exception(e)
        disconnect(close_valves=False)
