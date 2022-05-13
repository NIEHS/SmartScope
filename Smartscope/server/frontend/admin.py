from django.contrib import admin
from Smartscope.server.models import *
# Register your models here.

admin.site.register(ScreeningSession)
admin.site.register(HoleType)
admin.site.register(MeshSize)
admin.site.register(MeshMaterial)
admin.site.register(Microscope)
admin.site.register(Detector)
admin.site.register(AutoloaderGrid)
admin.site.register(GridCollectionParams)
admin.site.register(Finder)
admin.site.register(Classifier)
