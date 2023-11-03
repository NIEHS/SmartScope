import os
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
# from django.contrib import admin
from django.conf import settings
from django.urls import path, include, re_path
from .viewsets import *
from .views import *

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'holetypes', HoleTypeViewSet)
router.register(r'meshsizes', MeshSizeViewSet)
router.register(r'meshmaterial', MeshMaterialViewSet)
router.register(r'microscopes', MicroscopeViewSet)
router.register(r'detectors', DetectorViewSet)
router.register(r'sessions', ScreeningSessionsViewSet)
router.register(r'grids', AutoloaderGridViewSet)
router.register(r'atlas', AtlasModelViewSet)
router.register(r'squares', SquareModelViewSet)
router.register(r'holes', HoleModelViewSet)
router.register(r'highmag', HighMagModelViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('convert', ConvertAWS.as_view()),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('assing-bis-groups', AssingBisGroupsView.as_view()),
    path('updatetargets/', UpdateTargetsView.as_view()),
    path('addtargets/', AddTargets.as_view()),
    path('sidepanel/', SidePanel.as_view()),
    path('report/', ReportPanel.as_view()),
    # path('squares', SquareListView.as_view())
]

if settings.ALTERNATE_LOGIN:
    urlpatterns += [
        path('login/', AlternateLoginView.as_view(), name='login'),
        path('logout/', AlternateLogoutView.as_view(), name='logout')
    ]
