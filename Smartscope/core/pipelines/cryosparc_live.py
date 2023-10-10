
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

class CryoSPARCPipelineForm(forms.Form):
    cs_address = forms.URLField(label='CryoSPARC URL:',help_text='Web address of CryoSPARC installation (must be accessible from the SmartScope computer).')
    cs_port = forms.IntegerField(label='CryoSPARC Port:',help_text='Port of CryoSPARC installation. Defaults to 39000 if not set')
    cs_license = forms.CharField(label='CryoSPARC License Key',help_text='CryoSPARC License Key')
    cs_email = forms.CharField(label='CryoSPARC User Email',help_text='CryoSPARC User Email Address')
    cs_password = forms.CharField(label='CryoSPARC User Password',help_text='CryoSPARC User Password')
    cs_project = forms.IntegerField(label='CryoSPARC Project # P',
        help_text='Enter the project number of the CryoSPARC project you would like to spawn the Live sessions in. Omit the P at the beginning'
        ) 
    cs_worker_processes=forms.IntegerField(label='# of pre-processing workers:',help_text='Number of worker processes to spawn')
    cs_preprocessing_lane = forms.CharField(label='Name of pre-processing lane:',help_text='Name of lane to use for CryoSPARC Live preprocessing lane')
    frames_directory = forms.CharField(help_text='Locations to look for the frames file other. '+ \
        'Will look in the default smartscope/movies location by default.')

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
    frames_directory:Union[Path,None] = None

    @validator('frames_directory')
    def is_frame_directory_empty(cls,v):
        logger.debug(f'{v}, {type(v)}')
        if v == '' or v == Path('.'):
            return None
        return v


class CryoSPARC(PreprocessingPipeline):
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
        self.frames_directory = [Path(self.detector.frames_directory)]
        if self.cmd_data.frames_directory is not None:
            self.frames_directory.append(self.cmd_data.frames_directory)
        self.license = self.cmd_data.cs_license
        self.host = self.cmd_data.cs_address
        self.base_port = self.cmd_data.cs_port
        self.email = self.cmd_data.cs_email
        self.password = self.cmd_data.cs_password

    def start(self): #Abstract Class Function - Required

        cs_instance = CryoSPARC(license=self.cmd_data.cs_license, host=self.cmd_data.cs_address, base_port=self.cmd_data.cs_port, email=self.cmd_data.cs_email, password=self.cmd_data.cs_password)
        print(str(cs_instance.test_connection()))

    def stop(self):  #Abstract Class Function - Required
        pass

    def check_for_update(self, instance):  #Abstract Class Function - Required
        pass

