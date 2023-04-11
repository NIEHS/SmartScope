import logging
from pathlib import Path
import yaml
import os
from Smartscope.lib.s3functions import TemporaryS3File
from Smartscope.core.settings.worker import PROTOCOLS_FACTORY, SMARTSCOPE_CUSTOM_CONFIG
from Smartscope.lib.Datatypes.base_protocol import BaseProtocol
from Smartscope.lib.converters import rgetattr

logger = logging.getLogger(__name__)

def load_protocol(file:Path):
    if file.exists():
        with open(file) as f:
            return BaseProtocol.parse_obj(yaml.safe_load(f))

    # if eval(os.getenv('USE_AWS')):
    #     with TemporaryS3File([file]) as temp:
    #         with open(temp.temporary_files[0]) as f:
    #             return yaml.safe_load(f)

class AutoProtocol:
    rules_file = SMARTSCOPE_CUSTOM_CONFIG / 'default_protocols.yaml'

    def __init__(self,grid):
        self.grid = grid
        self.load_default_protocol_rules()

    def load_default_protocol_rules(self):
        with open(self.rules_file,'r') as f:
            self.rules = yaml.safe_load(f)

    def parse_rules(self):
        for rule in self.rules:
            conditions = [self.check_condition(*condition) for condition in rule['conditions']]
            mode = rule.pop('mode',None)
            if mode == 'any':
                if any(conditions):
                    return rule['protocol']
            if all(conditions):
                return rule['protocol']            

    def check_condition(self,attr,val):
        attribute = rgetattr(self.grid,attr)
        if not isinstance(val,str):
            return attribute == val
        val = val.split('__')
        if len(val) == 1:
            return attribute == val[0]
        try:
            value = eval(val[1])
        except:
            value = val[1]
        if val[0] == '!':
            return attribute != value
        return attribute == value
       
                
def save_protocol(protocol, file='protocol.yaml'):
    with open(file, 'w') as f:
        yaml.dump(protocol.dict(), f)

def set_protocol(protocol_name:str,protocol_file:Path):
    protocol = PROTOCOLS_FACTORY[protocol_name]
    save_protocol(protocol,protocol_file)
    return protocol

def get_or_set_protocol(grid, protocol_name:str='auto', force_set=False):
    if (protocol:=load_protocol(file=grid.protocol)) is not None and not force_set:
        logger.debug(f'Loading protocol from file')
        return protocol
    if protocol_name == 'auto':
        logger.debug(f'Automatically setting up protocol')
        protocol= AutoProtocol(grid).parse_rules()
        return set_protocol(protocol,grid.protocol)
    return set_protocol(protocol_name,grid.protocol)