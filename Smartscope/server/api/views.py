from django.http import HttpResponse
from rest_framework import response
from Smartscope.lib.db_manipulations import update, update_target
from Smartscope.core.models import *
from .serializers import *
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from Smartscope.server.lib.s3functions import *
from Smartscope.server.frontend.forms import *
from django.db import transaction
from Smartscope.server.lib.worker_jobs import send_to_worker
from django.contrib.auth.models import User, Group
from rest_framework.renderers import TemplateHTMLRenderer
import json
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

    def patch(self, request, format=None):
        data = request.data
        logger.debug(request.user)
        logger.debug(data)
        response = update_target(data)
        return Response(response)


class AddTargets(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        data = request.data

        out, err = send_to_worker(os.getenv('SMARTSCOPE_EXE'),
                                  arguments=['add_single_targets', data['square_id'], ' '.join([f'{i[0]},{i[1]}' for i in data['targets']])], communicate=True, timeout=30)
        logger.debug(out.decode("utf-8"))
        logger.debug(err.decode("utf-8"))
        response = dict(success=True, targets_added=len(data['targets']))
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
            context['gridform'] = AutoloaderGridReportForm(instance=context['grid'])
            context['gridCollectionParamsForm'] = GridCollectionParamsForm(instance=context['grid'].params_id)
            try:
                context['atlas_id'] = context['grid'].atlasmodel_set.all().first().atlas_id
            except:
                context['atlas_id'] = None
            # self.directory = context['grid'].directory

            return Response(context, content_type='html')
        else:
            return HttpResponse(f'Sorry, {user} is not allowed to view this content.')
