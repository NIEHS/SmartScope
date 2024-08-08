from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.auth import login, logout
from django.shortcuts import resolve_url
from django.shortcuts import redirect

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.renderers import TemplateHTMLRenderer

from Smartscope.lib.image.smartscope_storage import SmartscopeStorage
from Smartscope.server.frontend.forms import *
from Smartscope.server.lib.worker_jobs import send_to_worker
from Smartscope.core.db_manipulations import update, update_target_selection, update_target_label, update_target_status
from Smartscope.core.main_commands import list_plugins, reload_plugins
from Smartscope.core.models import *
from .serializers import *


import jwt
import logging


logger = logging.getLogger(__name__)
# smartscopeServerLog = logging.getLogger('smartscope.server')

# class ScreeningSessionsListView(generics.ListAPIView):
#     queryset = ScreeningSession.objects.all()
#     serializer_class = SessionSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['session', 'group', 'date', 'microscope_id', 'detector_id']


# class AutoloaderGridListView(generics.ListAPIView):
#     queryset = AutoloaderGrid.objects.all()
#     serializer_class = AutoloaderGridSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['session_id', 'holeType', 'meshSize', 'meshMaterial', 'quality']


# class AtlasListView(generics.ListAPIView):
#     queryset = AtlasModel.objects.all()
#     serializer_class = AtlasSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType', 'grid_id__meshSize', 'grid_id__quality']


# class SquareListView(generics.ListAPIView):
#     queryset = SquareModel.objects.all()
#     serializer_class = AtlasSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType', 'grid_id__meshSize', 'grid_id__quality',
#                         'atlas_id', 'quality', ]

class AlternateLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self,request):
        encrypted_user = request.query_params.get('user')
        logger.debug(f"Encrypted user: {encrypted_user}")
        decrypted_user = jwt.decode(encrypted_user, settings.SECRET_KEY, algorithms=["HS256"])
        logger.debug(f"Decrypted user: {decrypted_user}")
        user = User.objects.filter(username=decrypted_user['username']).first()
        if user is None:
            return redirect(settings.ALTERNATE_LOGIN_URL + '/login/usernotfound')
        # if not user.is_authenticated:
        logger.debug(f"User {user} is not authenticated")
        if (expiry:=request.query_params.get('expiry',None)) is not None:
            logger.debug(f"Setting session expiry to {expiry}")
            request.session.set_expiry(int(expiry))
        login(request, user)
        return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))
        
class AlternateLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self,request):
        logger.debug(f'Alternate Logout request received from {request.user}')
        logout(request)
        url = settings.ALTERNATE_LOGIN_URL + '/logoutcallback'
        logger.debug('Returning to ' + url)
        return redirect(url)



class AssingBisGroupsView(APIView):
    pass


class ConvertAWS(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        """
        Return a list of all users.
        """
        storage = SmartscopeStorage()
        res = storage.url(request.query_params['key'])
        return Response(res)


class UpdateTargetsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    _MODELS = {'holes': HoleModel,
               'squares': SquareModel}
    
    _KEYS = {'selected': update_target_selection,
             'status': update_target_status,
                'label': update_target_label}

    response = dict(success=False, error=None)

    def patch(self, request, format=None):
        data = request.data
        logger.debug(request.user)
        logger.debug(data)
        model = self._MODELS.get(data.pop('type'),False)
        function = self._KEYS.get(data.pop('key'),False)
        method = data.pop('method',None)
        if not model or not function:
            self.response['error'] = f'Model or method invalid.'
            return Response(self.response)
        objects_ids = data.pop('ids',[])
        function(model=model,objects_ids=objects_ids,value=data.pop('new_value'),method=method)
        try:
            instance = model.objects.get(pk=objects_ids[0]).parent
            response = SvgSerializer(instance=instance, display_type=data.pop('display_type','classifiers'), method=method).data
            response['success'] = True
        except Exception as err:
            logger.exception(f"An error occured while updating the page. {err}")
        return Response(response)


class AddTargets(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        data = request.data
        microscope_id = ScreeningSession.objects.get(pk=data['session_id']).microscope_id
        logger.debug('Adding targets')
        try:
            out, err = send_to_worker(microscope_id.worker_hostname, microscope_id.executable,
                                      arguments=['add_single_targets', data['square_id'], ' '.join([f'{i[0]},{i[1]}' for i in data['targets']])], communicate=True, timeout=30)
            success = True
        except Exception as err:
            logger.exception(err)
            success = False
        logger.debug(out.decode("utf-8"))
        logger.debug(err.decode("utf-8"))
        response = dict(success=success, targets_added=len(data['targets']))
        return Response(response)


class SidePanel(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'sidepanel.html'
    jsfunction = 'loadSidePanel'

    def get(self, request):
        logger.debug(request.query_params)
        group = request.query_params.get('group')
        session = request.query_params.get('session_id')
        user = request.user
        field = None
        if group is not None and (user.is_staff or user.groups.filter(pk=group).exists()):
            # if group is not None:
            group = Group.objects.get(pk=group)
            items = list(ScreeningSession.objects.filter(group=group).order_by('-date'))
            nextsection = 'sidebarGrids'
            field = 'session_id'

        if session is not None:

            session = ScreeningSession.objects.get(pk=session)
            if user.is_staff or user.groups.filter(name=session.group).exists():
                items = list(AutoloaderGrid.objects.filter(session_id=session).order_by('position'))
                nextsection = None
                field = 'grid_id'
                self.jsfunction = "loadReport"

        if field is None:
            if user.is_staff:
                items = Group.objects.all().exclude(name='viewer_only')
            else:
                items = list(user.groups.all().exclude(name='viewer_only'))
            nextsection = 'sidebarSessions'
            field = 'group'

        for item in items:
            item.extraCSS = ''
            if hasattr(item, 'quality'):
                item.extraCSS = f'quality-{item.quality}'

        return Response(dict(items=items, nextsection=nextsection, field=field, jsfunction=self.jsfunction))


class ReportPanel(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'report.html'

    def get(self, request):
        # smartscopeServerLog.info(request.query_params)
        grid_id = request.query_params.get('grid_id')
        grid = AutoloaderGrid.objects.get(grid_id=grid_id)
        user = request.user
        user_groups = list(user.groups.values_list('pk', flat=True))
        group = grid.session_id.group
        logger.debug(f"Group={group.pk}, {user_groups}")

        if user.is_staff or group.pk in user_groups:
            context = dict()
            context['grid'] = grid
            context['tagsFeatureFlag'] = settings.TAGS_FEATURE_FLAG
            context['gridform'] = AutoloaderGridReportForm(instance=context['grid'])
            context['gridCollectionParamsForm'] = GridCollectionParamsForm(instance=context['grid'].params_id, grid_id=context['grid'].grid_id)
            context['useMicroscope'] = settings.USE_MICROSCOPE
            try:
                context['atlas_id'] = context['grid'].atlasmodel_set.all().first().atlas_id
            except:
                context['atlas_id'] = None
            # self.directory = context['grid'].directory

            return Response(context, content_type='html')
        else:
            return HttpResponse(f'Sorry, {user} is not allowed to view this content.')

class PluginView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        logger.debug('PluginView')
        plugins = list_plugins()
        logger.debug(plugins)
        return Response(plugins.keys())

    def post(self, request):
        logger.debug('Reloading plugins')
        reload_plugins()
        return Response('Plugins reloaded')