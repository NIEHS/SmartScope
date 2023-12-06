import logging
from .fakescope_interface import FakeScopeInterface
from .microscope import Microscope, Detector, AtlasSettings, MicroscopeState

logger = logging.getLogger(__name__)

def generate_mock_fake_scope_interface() -> FakeScopeInterface:
    microscope = Microscope(loader_size=12,
                            serialem_IP='xxx.xxx.xxx.xxx',
                            serialem_PORT=48888, 
                            windows_path='X:\\\\smartscope',
                            scope_path='/mnt/fake_scope/',)
    detector = Detector(energy_filter=False, frames_windows_directory='X:\\\\smartscope\\frames')
    atlas_settings = AtlasSettings(atlas_mag=10000, atlas_max_tiles_X=10, atlas_max_tiles_Y=10, spot_size=3, c2_perc=0.5, atlas_to_search_offset_x=0, atlas_to_search_offset_y=0)
    return FakeScopeInterface(microscope=microscope, detector=detector, atlas_settings=atlas_settings)