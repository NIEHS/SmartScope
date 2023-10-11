
from functools import partial
import time
from typing import Dict

import multiprocessing
import logging
from pathlib import Path

from Smartscope.core.db_manipulations import websocket_update
from Smartscope.core.models.grid import AutoloaderGrid
from Smartscope.lib.preprocessing_methods import get_CTFFIN4_data, \
    process_hm_from_average, process_hm_from_frames, processing_worker_wrapper
from Smartscope.core.models.models_actions import update_fields

from django.db import transaction

from .preprocessing_pipeline import PreprocessingPipeline
from .smartscope_preprocessing_pipeline_form import SmartScopePreprocessingPipelineForm
from .smartscope_preprocessing_cmd_kwargs import SmartScopePreprocessingCmdKwargs

from typing import Union
from pathlib import Path
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

from django import forms
from cryosparc.tools import CryoSPARC

class CryoSPARCPipelineForm(forms.Form):
    cs_address = forms.CharField(label='CryoSPARC URL:',help_text='Web address of CryoSPARC installation (must be accessible from the SmartScope computer).')
    cs_port = forms.IntegerField(label='CryoSPARC Port:',help_text='Port of CryoSPARC installation. Defaults to 39000 if not set')
    cs_license = forms.CharField(label='CryoSPARC License Key',help_text='CryoSPARC License Key')
    cs_email = forms.CharField(label='CryoSPARC User Email',help_text='CryoSPARC User Email Address')
    cs_password = forms.CharField(label='CryoSPARC User Password',help_text='CryoSPARC User Password')
    cs_project = forms.IntegerField(label='CryoSPARC Project # P',help_text='Enter the project number of the CryoSPARC project you would like to spawn the Live sessions in. Omit the P at the beginning')
    cs_worker_processes=forms.IntegerField(label='# of pre-processing workers:',help_text='Number of worker processes to spawn')
    cs_preprocessing_lane = forms.CharField(label='Name of pre-processing lane:',help_text='Name of lane to use for CryoSPARC Live preprocessing lane')
    frames_directory = forms.CharField(help_text='Absolute path for frame directory relative to CryoSPARC Master instance')
    cs_dose=forms.FloatField(label='Dose',help_text='Total dose in e/A2')
    cs_apix=forms.FloatField(label='Pixel Size',help_text='Angstroms per pixel')
    cs_lanes=forms.CharField(label='Worker Lane',help_text='Name of CryoSPARC Live Worker Lane')

    def __init__(self, *args,**kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.required = False

class CryoSPARCCmdKwargs(BaseModel):
    cs_address:str = ""
    cs_port:int = 39000
    cs_license:str = ""
    cs_email:str = ""
    cs_password:str = ""
    cs_project:int = 9999
    cs_worker_processes:int = 1
    cs_preprocessing_lane:str = ""
    frames_directory:str = ""
    cs_dose:float = 50.0
    cs_apix:float = 1.0
    cs_lanes:str = ""


class CryoSPARCPipeline(PreprocessingPipeline):
    verbose_name = 'CryoSPARC Live Pre-Processing Pipeline'
    name = 'cryoSPARC'
    description = 'Spawn CryoSPARC Live sessions at each grid. Requires a functional CryoSPARC installation.'
    to_process_queue = multiprocessing.JoinableQueue()
    processed_queue = multiprocessing.Queue()
    child_process = []
    to_update = []
    incomplete_processes = []
    cmdkwargs_handler = CryoSPARCCmdKwargs
    pipeline_form= CryoSPARCPipelineForm

    def __init__(self, grid: AutoloaderGrid, cmd_data:Dict):
        super().__init__(grid=grid)
        self.microscope = self.grid.session_id.microscope_id
        self.detector = self.grid.session_id.detector_id
        self.cmd_data = self.cmdkwargs_handler.parse_obj(cmd_data)
        logger.debug(self.cmd_data)

        self.license = self.cmd_data.cs_license
        self.host = self.cmd_data.cs_address
        self.base_port = self.cmd_data.cs_port
        self.email = self.cmd_data.cs_email
        self.password = self.cmd_data.cs_password
        self.project = 'P' + str(self.cmd_data.cs_project)
        self.frames_directory = self.cmd_data.frames_directory
        self.dose = self.cmd_data.cs_dose
        self.apix = self.cmd_data.cs_apix
        self.lane = self.cmd_data.cs_lanes

        cs_session = ""

    def start(self): #Abstract Class Function - Required

        #Setup connection to CryoSPARC Instance
        cs_instance = CryoSPARC(license=self.license,host=self.host,base_port=self.base_port,email=self.email,password=self.password)
        csparc_debug = str(cs_instance.test_connection())
        logger.debug(f'CryoSPARC Connection Test: {csparc_debug}')

        #Need to check here if session already exists. If so, skip creation, if not, create.

        #Create new CryoSPARC Live session
        cs_session = cs_instance.rtp.create_new_live_workspace(project_uid=str(self.project), created_by_user_id=str(cs_instance.cli.get_id_by_email(self.email)), title=str(self.grid.session_id))

        #Setup lanes
        cs_instance.rtp.update_compute_configuration(project_uid=str(self.project), session_uid=cs_session, key='phase_one_lane', value=str(self.lane))
        cs_instance.rtp.update_compute_configuration(project_uid=str(self.project), session_uid=cs_session, key='phase_one_gpus', value=2)
        cs_instance.rtp.update_compute_configuration(project_uid=str(self.project), session_uid=cs_session, key='phase_two_lane', value=str(self.lane))
        cs_instance.rtp.update_compute_configuration(project_uid=str(self.project), session_uid=cs_session, key='auxiliary_lane', value=str(self.lane))

        #Setup exposure group
        cs_instance.rtp.exposure_group_update_value(project_uid=str(self.project), session_uid=cs_session, exp_group_id=1, name='file_engine_watch_path_abs', value=str(self.frames_directory))
        cs_instance.rtp.exposure_group_update_value(project_uid=str(self.project), session_uid=cs_session, exp_group_id=1, name='file_engine_filter', value='.tif')
        cs_instance.rtp.exposure_group_finalize_and_enable(project_uid=str(self.project), session_uid=cs_session, exp_group_id=1)

        #Motion Correction Settings
        cs_instance.rtp.set_param(project_uid=str(self.project), session_uid=cs_session, param_sec='mscope_params', param_name='accel_kv', value=float(self.microscope.voltage))
        cs_instance.rtp.set_param(project_uid=str(self.project), session_uid=cs_session, param_sec='mscope_params', param_name='cs_mm', value=float(self.microscope.spherical_abberation))

        ##Need to check for if files have been written here, and get values from .mdoc file.
        cs_instance.rtp.set_param(project_uid=str(self.project), session_uid=cs_session, param_sec='mscope_params', param_name='total_dose_e_per_A2', value=float(self.dose))
        cs_instance.rtp.set_param(project_uid=str(self.project), session_uid=cs_session, param_sec='mscope_params', param_name='psize_A', value=float(self.apix))
        ##Also need gain controls here (Flip/rotate)

        #Extraction Settings
        cs_instance.rtp.set_param(project_uid=str(self.project), session_uid=cs_session, param_sec='blob_pick', param_name='diameter', value=100)
        cs_instance.rtp.set_param(project_uid=str(self.project), session_uid=cs_session, param_sec='blob_pick', param_name='diameter_max', value=200)
        cs_instance.rtp.set_param(project_uid=str(self.project), session_uid=cs_session, param_sec='extraction', param_name='box_size_pix', value=440)

        #Start the session
        cs_instance.rtp.start_session(project_uid=str(self.project), session_uid=cs_session, user_id=cs_instance.cli.get_id_by_email(self.email))

    def stop(self):  #Abstract Class Function - Required
        #Turn off live session
        cs_instance.rtp.pause_session(project_uid=str(self.project), session_uid=cs_session)

    def check_for_update(self, instance):  #Abstract Class Function - Required
        #Here should probably go some logic that will get the hole and image, check CryoSPARC for existing thumbnail and data, and update the object
        pass
