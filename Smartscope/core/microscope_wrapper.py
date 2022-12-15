from functools import partial
from typing import Callable
from Smartscope.lib.Datatypes.microscope import MicroscopeInterface

def set_scope_atlas(scope:MicroscopeInterface,detector,params) -> Callable:
    return partial(scope.atlas,mag=detector.atlas_mag, c2=detector.c2_perc, spotsize=detector.spot_size,
                    tileX=params.atlas_x, tileY=params.atlas_y)


