from .fakescope_interface import FakeScopeInterface
from .tfsserialem_interface import TFSSerialemInterface
from .jeolserialem_interface import JEOLSerialemInterface

def select_microscope_interface(microscope):
    if microscope.serialem_IP == 'xxx.xxx.xxx.xxx':
        # logger.info('Setting scope into test mode')
        return FakeScopeInterface

    if microscope.vendor == 'JEOL':
        # logger.info('Using the JEOL interface')
        return JEOLSerialemInterface

    return TFSSerialemInterface