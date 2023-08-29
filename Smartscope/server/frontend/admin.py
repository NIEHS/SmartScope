from django.contrib import admin
# from Smartscope.core.models import *
# Register your models here.


# from Smartscope.core.models.grid import AutoloaderGrid
# from Smartscope.core.models.grid_collection_params import GridCollectionParams
from Smartscope.core.models.detector import Detector
from Smartscope.core.models.hole_type import HoleType
from Smartscope.core.models.mesh import MeshSize, MeshMaterial
from Smartscope.core.models.microscope import Microscope
# from Smartscope.core.models.screening_session import ScreeningSession
# from Smartscope.core.models.target import Finder, Classifier

# admin.site.register(ScreeningSession)
admin.site.register(HoleType)
admin.site.register(MeshSize)
admin.site.register(MeshMaterial)
admin.site.register(Microscope)
admin.site.register(Detector)
# admin.site.register(AutoloaderGrid)
# admin.site.register(GridCollectionParams)
# admin.site.register(Finder)
# admin.site.register(Classifier)
