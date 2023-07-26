import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Smartscope.core.settings.server_docker")
build_dir = os.path.dirname(os.path.dirname(__file__))
project_dir = os.path.join(build_dir, 'SmartScope')

import environ
env = environ.Env()
env_file = os.path.join(project_dir, 'S', 'core', 'settings', '.dev.env')
environ.Env.read_env(env_file=env_file)

import sys
sys.path.extend([build_dir, project_dir,])
import datetime
import multiprocessing

from Smartscope.core.autoscreen import run_grid

class Session:
    session='HQFJALIKY'
    date='20230208'
    version='0.8rc1'
    working_dir='BaiY/20230208_HQFJALIKY'
    session_id='20230208HQFJALIKYA3A3u8hc0yJ'
    detector_id_id='2'
    group_id='BaiY'
    microscope_id_id='VsHqmNJnbxSIE91Y1S8bPSeWToXUEP'

class MicroscopeModel:
    name='Krios'
    location='NIEHS'
    voltage='300'
    spherical_abberation='2.7'
    microscope_id='VsHqmNJnbxSIE91Y1S8bPSeWToXUEP'
    loader_size='12'
    worker_hostname='localhost'
    executable='smartscope.py'
    serialem_IP='192.168.0.31'
    serialem_PORT='40888'
    windows_path='X:\\smartscope\\'
    scope_path='/mnt/krios/'
    vendor='TFS'

class Microscope:
    loaderSize = 12
    ip = '192.168.0.31'
    port = 40888
    directory = 'X:\\\\smartscope\\'
    scopePath = '/mnt/krios/'



class AutoloaderGrid:
    position= 1
    name= 'HQFA_1'
    grid_id= '1HQFA_1PsgICFvlu4TIYqm9V4DYTr3'
    session_id_id= '20230208HQF-JAL-IKYA3A3u8hc0yJ'
    holeType_id= 'Lacey'
    meshSize_id= '300'
    meshMaterial_id= 'Carbon'
    hole_angle= None
    mesh_angle= None
    quality= None 
    notes= None
    status= 'started' 
    start_time= datetime.datetime(2023, 7, 17, 14, 52, 1, 315816, tzinfo=datetime.timezone.utc) 
    last_update= datetime.datetime(2023, 7, 17, 15, 0, 50, 554141, tzinfo=datetime.timezone.utc) 
    params_id_id= 'cnYqcnB0gEutZJ878xXQJde7wCZWda' 

class AtlasSettings:
    mag = 135
    maxX = 6
    maxY = 8
    spotSize = 5
    c2 = 520.0


class Detector:
    energyFilter = True
    framesDir = 'X:\\\\smartscope\\movies'


class Grid:
    position = 1
    name = 'HQFA_1'
    grid_id = '1HQFA_1PsgICFvlu4TIYqm9V4DYTr3'
    session_id_id = '20230208HQF-JAL-IKYA3A3u8hc0yJ'
    holeType_id = 'Lacey'
    meshSize_id = '300' 
    meshMaterial_id = 'Carbon'
    hole_angle = None 
    mesh_angle = None 
    quality = None 
    notes = None
    status = 'started' 
    start_time = datetime.datetime(2023, 7, 17, 14, 52, 1, 315816, tzinfo=datetime.timezone.utc) 
    last_update = datetime.datetime(2023, 7, 17, 15, 0, 50, 554141, tzinfo=datetime.timezone.utc) 
    params_id_id = 'cnYqcnB0gEutZJ878xXQJde7wCZWda'
    prefetched_objects_cache = {}

class MicroscopeState:
    defocusTarget=0
    currentDefocus=0
    imageShiftX=0
    imageShiftY=0
    stageX=0
    stageY=0
    stageZ=0
    tiltAngle=None 
    preAFISimageShiftX=0
    preAFISimageShiftY=0
    has_hole_ref= False
    hole_crop_size = 0

class Scope:
    microscope = Microscope()
    detector = Detector()
    atlassettings = AtlasSettings()
    state = MicroscopeState()



if __name__ == "__main__":
    session = Session()
    grid = Grid()
    scope = Scope()
    processing_queue = multiprocessing.JoinableQueue()
    run_grid(grid, session, processing_queue, scope)
