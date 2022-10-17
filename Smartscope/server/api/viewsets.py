from django.contrib.auth.models import User, Group
import mrcfile
import mrcfile.mrcinterpreter
import mrcfile.mrcfile
from rest_framework import viewsets
from rest_framework import permissions
from Smartscope.core.models.models_actions import targets_methods
from Smartscope.server.api.permissions import HasGroupPermission
from .serializers import *
from Smartscope.core.models import *
from Smartscope.server.frontend.forms import *
from rest_framework.decorators import action
from rest_framework.response import Response
from django.template.response import SimpleTemplateResponse
from django.http import FileResponse
from django.template.loader import render_to_string
from django.db import transaction
import base64
from Smartscope.lib.montage import power_spectrum
from Smartscope.lib.system_monitor import disk_space
from Smartscope.core.db_manipulations import get_hole_count, viewer_only
from Smartscope.lib.converters import *
from Smartscope.server.lib.worker_jobs import send_to_worker
from django.conf import settings
import json
import os
import time
import logging
from rest_framework.renderers import TemplateHTMLRenderer
from pathlib import Path

logger = logging.getLogger(__name__)


class ExtraActionsMixin:

    def load(self, request, **kwargs):
        obj = self.queryset.filter(pk=kwargs['pk']).first()
        serializer = SvgSerializer(instance=obj, context={'request': request})
        context = serializer.data
        return Response(serializer.data, template_name='mapcard.html')

    def load_card(self, request, **kwargs):
        context = dict()
        obj = self.queryset.filter(pk=kwargs['pk']).first()
        display_type = isnull_to_none(request.query_params['display_type'])
        context['display_type'] = 'classifiers' if display_type is None else display_type
        context['method'] = isnull_to_none(request.query_params['method'])
        context['targets_methods'] = targets_methods(obj)
        context['instance'] = obj
        if context['method'] is None:
            methods = context['targets_methods'][context['display_type']]
            if len(methods) > 0:
                context['method'] = methods[0].name
        serializer = SvgSerializer(instance=obj, display_type=context['display_type'], method=context['method'])
        context = {**context, **serializer.data}
        context['card'] = render_to_string('mapcard.html', context=context, )
        logger.debug(f"{context['method']}, {context['display_type']}")
        return Response(dict(fullmeta=context['fullmeta'], card=context['card'], displayType=context['display_type'], method=context['method']))

    @ action(detail=True, methods=['get'])
    def file_paths(self, request, *args, **kwargs):
        self.serializer_class = FilePathsSerializer
        serializer = self.get_serializer(self.get_object(), many=False)
        return Response(serializer.data)

    @ action(detail=True, methods=['get'])
    def download(self, request, **kwargs):
        extension = request.query_params.get('extension', None)
        if extension is None:
            extension = 'mrc'
        instance = self.get_object()
        extension_factory = {
            'mrc': 'mrc',
            'raw': 'raw_mrc',
            'png': 'png_img'
        }
        img = Path(getattr(instance, extension_factory[extension]))
        response = FileResponse(open(img, 'rb'), content_type='image/*')
        response['Content-Length'] = os.path.getsize(img)
        response['Content-Disposition'] = f"attachment; filename={img.name}"
        return response


class TargetRouteMixin:

    detailed_serializer = None

    def get_detailed_serializer(self):
        if self.detailed_serializer is None:
            raise ValueError(f'detailed_serializer attribute is not set on {self.__class__.__name__}.')
        return self.detailed_serializer

    @ action(detail=True, methods=['get'], url_path='detailed')
    def detailedOne(self, request, *args, **kwargs):
        self.serializer_class = self.get_detailed_serializer()
        obj = self.get_object()
        serializer = self.get_serializer(obj, many=False)
        return Response(data=serializer.data)

    @ action(detail=False, methods=['get'], url_path='detailed')
    def detailedMany(self, request, *args, **kwargs):
        self.serializer_class = self.get_detailed_serializer()
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAdminUser]


class MicroscopeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows ScreeningSessions to be viewed or edited.
    """
    queryset = Microscope.objects.all()
    serializer_class = MicroscopeSerializer
    permission_classes = [permissions.IsAuthenticated]


class DetectorViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows ScreeningSessions to be viewed or edited.
    """
    queryset = Detector.objects.all()
    serializer_class = DetectorSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScreeningSessionsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows ScreeningSessions to be viewed or edited.
    """
    queryset = ScreeningSession.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]

    filterset_fields = ['session', 'group', 'date', 'microscope_id', 'detector_id']

    @ action(detail=True, methods=['post'],)
    def run_session(self, request, **kwargs):
        self.object = self.get_object()
        data = request.data

        if 'start' in data.keys() and not viewer_only(request.user):
            process_init = process = self.object.process_set.first()
            if data['start'] is True:
                logger.info('starting process')
                send_to_worker(self.object.microscope_id.worker_hostname, self.object.microscope_id.executable,
                               arguments=['autoscreen', self.object.session_id],)
                # send_to_worker('which Smartscope.sh', communicate=True)
            else:
                logger.info('stopping')
                # send_to_worker(self.object.microscope_id.worker_hostname, 'kill', arguments=['-15', process.PID])
                send_to_worker(self.object.microscope_id.worker_hostname, self.object.microscope_id.executable,
                               arguments=['stop_session', self.object.session_id])

            rounds = 0
            check = True
            while check:
                logger.info('Starting checks')
                rounds += 1
                if rounds > 15:
                    return Response({'error': 'Command Timeout reached', 'isRunning': process.status == 'running', 'pid': process.PID, 'status': process.status})
                time.sleep(1)
                process = self.object.process_set.first()
                if process_init is None:
                    if process_init != process:
                        check = False
                else:
                    if process_init.status != process.status:
                        check = False

            return Response({'isRunning': process.status == 'running', 'pid': process.PID, 'status': process.status})

    @ action(detail=True, methods=['get'])
    def check_is_running(self, request, **kwargs):
        self.object = self.get_object()
        process = self.object.process_set.first()

        if process is not None:
            if process.status == 'running':
                return Response({'isRunning': True, 'pid': process.PID, 'status': process.status})
            else:
                return Response({'isRunning': False, 'pid': process.PID, 'status': process.status})
        return Response({'isRunning': False, 'pid': None, 'status': None})

    @ action(detail=True, methods=['put'])
    def pause_between_grids(self, request, **kwargs):
        self.object = self.get_object()
        data = request.data
        if 'pause' in data.keys():
            out, err = send_to_worker(self.object.microscope_id.worker_hostname, self.object.microscope_id.executable,
                                      arguments=['toggle_pause', self.object.microscope_id.pk], communicate=True)
            # print(out,err)
            out = out.decode("utf-8").strip().split('\n')[-1]
            # print(out)
            return Response(json.loads(out))

    @ action(detail=True, methods=['put'])
    def continue_run(self, request, **kwargs):
        self.object = self.get_object()
        data = request.data
        if 'continue' in data.keys():
            out, err = send_to_worker(self.object.microscope_id.worker_hostname, self.object.microscope_id.executable,
                                      arguments=['continue_run', data['continue'], self.object.microscope_id.pk], communicate=True)
            # print(out,err)
            out = out.decode("utf-8").strip().split('\n')[-1]
            # print(out)
            return Response(json.loads(out))

    @ action(detail=True, methods=['get'])
    def get_logs(self, request, **kwargs):
        self.object = self.get_object()
        logger.info('Fetching logs')
        check_output, err = send_to_worker(self.object.microscope_id. worker_hostname,
                                           self.object.microscope_id.executable, arguments=['check_pause', self.object.microscope_id.pk, self.object.session_id], communicate=True)
        logger.debug(f'Check pause output: {check_output}')
        check_output = json.loads(check_output.decode("utf-8").strip().split('\n')[-1])
        # check_stop_file_output = send_to_worker(self.object.microscope_id. worker_hostname,
        #                                         self.object.microscope_id.executable, arguments=['check_stop_file', self.object.session_id], communicate=True)
        disk_status = disk_space(settings.AUTOSCREENDIR)
        # try:
        out = self.read_file('run.out')
        proc = self.read_file('proc.out')
        queue = self.read_file('queue.txt', start_line=0)

        # except FileNotFoundError:
        #     out = ''
        #     proc = ''
        #     queue = ''

        return Response(dict(out=out, proc=proc, queue=queue, disk=disk_status, **check_output))

    @ action(detail=True, methods=['post'], )
    def force_kill(self, request, **kwargs):
        self.object = self.get_object()
        logger.info('stopping')
        out, err = send_to_worker(self.object.microscope_id.worker_hostname, 'pkill', arguments=['-f', self.object.pk])
        return Response(dict(out=out, err=err))

    @ action(detail=True, methods=['post'], )
    def remove_lock(self, request, **kwargs):
        self.object = self.get_object()
        logger.info('Removing lock file')
        out, err = send_to_worker(self.object.microscope_id.worker_hostname, 'rm', arguments=[
            os.path.join('/tmp/', f'{self.object.microscope_id.pk}.lock')], communicate=True)
        logger.info(f'OUTPUT: {out}\nERROR: {err}')
        return Response(dict(out=out, err=err))

    def read_file(self, name, start_line=-100):
        try:
            # print(os.path.join(self.object.directory, name))
            with open(os.path.join(self.object.directory, name), 'r') as f:
                file = ''.join(f.readlines()[start_line:])
            return file
        except FileNotFoundError as err:
            return ''

    def read_pid_file(self, timeout=10):
        timeout = time.time() + timeout
        pid_file = os.path.join(settings.TEMPDIR, f'{self.object.session_id}.pid')
        while time.time() < timeout:
            if os.path.isfile(pid_file):
                with open(pid_file, 'r') as f:
                    lines = f.readlines()
                pid = lines[0].strip()
                status = lines[1].strip()
                return pid, status
            else:
                logger.info('PID file not found, sleeping 2 sec')
                time.sleep(2)
        return None, 'No PID file found for session'


class MeshMaterialViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Mesh Material to be viewed or edited.
    """
    queryset = MeshMaterial.objects.all()
    serializer_class = MeshMaterialSerializer
    permission_classes = [permissions.IsAuthenticated]


class MeshSizeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Mesh Sizes to be viewed or edited.
    """
    queryset = MeshSize.objects.all()
    serializer_class = MeshSizeSerializer
    permission_classes = [permissions.IsAuthenticated]


class HoleTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Hole types to be viewed or edited.
    """
    queryset = HoleType.objects.all()
    serializer_class = HoleTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class AutoloaderGridViewSet(viewsets.ModelViewSet, ExtraActionsMixin):
    """
    API endpoint that allows Grids to be viewed or edited.
    """
    queryset = AutoloaderGrid.objects.all()
    serializer_class = AutoloaderGridSerializer
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    filterset_fields = ('session_id', 'holeType', 'meshSize', 'meshMaterial', 'quality', 'status')

    @ action(detail=True, methods=['get'])
    def fullmeta(self, request, **kwargs):
        obj = self.get_object()
        if obj.status is None:
            serializer = self.get_serializer(obj, many=False)
            data = serializer.data
            data['atlas'] = {}
            data['squares'] = {}
            data['holes'] = []
            data['counts'] = dict(completed=0, queued=0, perhour=0, lasthour=0)
            return Response(data)

        self.serializer_class = FullGridSerializer
        serializer = self.get_serializer(obj, many=False)
        data = serializer.data
        data['atlas'] = list_to_dict(data['atlas'])
        data['squares'] = list_to_dict(data['squares'])
        data['holes'] = []
        data['counts'] = get_hole_count(obj)
        return Response(data)

    @ action(detail=True, methods=['patch'])
    def editcollectionparams(self, request, **kwargs):
        obj = self.get_object()
        data = request.data
        logger.debug(data)
        try:
            form_params = GridCollectionParamsForm(data)
            logger.debug(form_params)
            if form_params.is_valid():
                params, created = GridCollectionParams.objects.get_or_create(**form_params.cleaned_data)
                logger.debug(f'Params newly created: {created}')
                obj.params_id = params
                obj.save()
                return Response(dict(success=True))
            else:
                logger.debug(f'Form invalid , {form_params}.')
                return Response(dict(success=False))
        except Exception as err:
            logger.error(f'Error while updating parameters, {err}.')
            return Response(dict(success=False))

    @ action(detail=True, methods=['get'])
    def export(self, resquest, **kwargs):
        obj = self.get_object()
        self.serializer_class = ExportMetaSerializer
        serializer = self.get_serializer(obj, many=False)
        return Response(data=serializer.data)


class AtlasModelViewSet(viewsets.ModelViewSet, ExtraActionsMixin):
    """
    API endpoint that allows Atlases to be viewed or edited.
    """
    queryset = AtlasModel.objects.all()
    serializer_class = AtlasSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType',
                        'grid_id__meshSize', 'grid_id__quality', 'grid_id__session_id', 'status']

    @ action(detail=True, methods=['get'])
    def load(self, request, **kwargs):
        return super().load_card(request, **kwargs)


class SquareModelViewSet(viewsets.ModelViewSet, ExtraActionsMixin, TargetRouteMixin):
    """
    API endpoint that allows Squares to be viewed or edited.
    """
    queryset = SquareModel.objects.all()
    serializer_class = SquareSerializer
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType', 'grid_id__meshSize', 'grid_id__quality',
                        'atlas_id', 'selected', 'grid_id__session_id', 'status']
    detailed_serializer = DetailedSquareSerializer

    @ action(detail=True, methods=['get'])
    def load(self, request, **kwargs):
        return super().load_card(request, **kwargs)

    @ action(detail=True, methods=['patch'],)
    def all(self, request, **kwargs):
        try:
            obj = self.get_object()
            action = request.data['action']
            is_bis = obj.grid_id.params_id.bis_max_distance > 0
            if action == 'addall':
                query_filters = dict(selected=False)
                if is_bis:
                    query_filters['bis_type'] = 'center'
                    query_filters['bis_group__isnull'] = False
                query = obj.holemodel_set.all().filter(**query_filters)
                selected = True
            elif action == 'cancelall':
                query_filters = dict(selected=True, status='queued')
                query = obj.holemodel_set.all().filter(**query_filters)
                selected = False

            with transaction.atomic():
                for target in query:
                    target.selected = selected
                    target.save()
            return Response(data=dict(success=True))
        except Exception as err:
            logger.exception(err)
            return Response(data=dict(success=False))

    @ action(detail=True, methods=['patch'])
    def regroup_bis(self, request, *args, **kwargs):

        logger.debug('Regrouping BIS')
        try:
            obj = self.get_object()
            microscope = obj.grid_id.session_id.microscope_id
            out, err = send_to_worker(microscope.worker_hostname, microscope.executable, arguments=[
                'regroup_bis', obj.grid_id.pk, obj.square_id], communicate=True, timeout=30)
            out = out.decode("utf-8").strip().split('\n')[-1]
            return Response(dict(out=out))
        except Exception as err:
            logger.error(f'Error tring to regrouping BIS, {err}')
            return Response(dict(success=False))


class HoleModelViewSet(viewsets.ModelViewSet, ExtraActionsMixin, TargetRouteMixin):
    """
    API endpoint that allows Squares to be viewed or edited.
    """
    queryset = HoleModel.objects.all()
    serializer_class = HoleSerializer
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType', 'grid_id__meshSize', 'grid_id__quality', 'grid_id__session_id',
                        'square_id', 'status', 'bis_group', 'bis_type']

    detailed_serializer = DetailedHoleSerializer

    @ action(detail=False, methods=['get'])
    def simple(self, request, *args, **kwargs):
        self.serializer_class = HoleSerializerSimple
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @ action(detail=True, methods=['get'])
    def highmag(self, request, *args, **kwargs):
        obj = self.get_object()
        # self.serializer_class = HighMagSerializer
        self.renderer_classes = [TemplateHTMLRenderer]

        if obj.bis_group is None:
            queryset = list(HighMagModel.objects.filter(hole_id=kwargs['pk']))
        else:
            queryset = list(HighMagModel.objects.filter(grid_id=obj.grid_id,
                                                        hole_id__bis_group=obj.bis_group, status='completed').order_by('is_x', 'is_y'))
        context = dict(holes=queryset)
        context['classifier'] = PLUGINS_FACTORY['Micrographs curation']
        resp = SimpleTemplateResponse(context=context, content_type='text/html', template='holecard.html')
        logger.debug(resp)
        return resp
        # return Response(context, template_name='holecard.html', content_type='text/html',renderer=TemplateHTMLRenderer)
        # return Response(list_to_dict(serializer.data))

    @ action(detail=False, methods=['get'])
    def preload_highmag(self, request, *args, **kwargs):
        extra_filters = dict()
        numToLoad = int(self.request.query_params.get('number'))
        grid_id = self.request.query_params.get('grid_id')
        if grid_id:
            extra_filters = dict(grid_id=grid_id)
        self.serializer_class = DetailedHoleSerializer
        count = HoleModel.objects.filter(status='completed', quality__isnull=True, **extra_filters).count()
        self.queryset = HoleModel.objects.filter(status='completed', quality__isnull=True, **extra_filters).order_by('?')[: numToLoad]
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(dict(data=serializer.data, count=count))


class HighMagModelViewSet(viewsets.ModelViewSet, ExtraActionsMixin):
    """
    API endpoint that allows Atlases to be viewed or edited.
    """
    queryset = HighMagModel.objects.all()
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    serializer_class = HighMagSerializer
    filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType', 'grid_id__meshSize',
                        'grid_id__quality', 'hole_id', 'hole_id__square_id', 'grid_id__session_id', 'hm_id']

    @ action(detail=True, methods=['get'])
    def fft(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.is_aws:
            storage = SmartscopeStorage()
            file = storage.download_temp(obj.raw_mrc)
            with mrcfile.open(file, 'r') as mrc:
                img = mrc.data
            os.remove(file)

        else:
            with mrcfile.open(obj.raw_mrc, 'r') as mrc:
                img = mrc.data

        fft = power_spectrum(img)
        return Response(dict(img=base64.b64encode(fft.getvalue())))
