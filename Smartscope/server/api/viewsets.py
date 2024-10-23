from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import connection, reset_queries, transaction
from django.template.response import SimpleTemplateResponse
from django.http import FileResponse
from django.template.loader import render_to_string
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework import status as rest_status
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.decorators import action
from rest_framework.response import Response

import base64
import io
import json
import os
import time
import logging
from pathlib import Path
import mrcfile
import mrcfile.mrcinterpreter
import mrcfile.mrcfile

from .serializers import *
from Smartscope.server.api.permissions import HasGroupPermission
from Smartscope.server.frontend.forms import *

from Smartscope.lib.converters import list_to_dict, get_request_param
from Smartscope.lib.image_manipulations import power_spectrum
from Smartscope.utils.system_monitor import disk_space
from Smartscope.server.lib.worker_jobs import send_to_worker

from Smartscope.core.models.models_actions import targets_methods
from Smartscope.core.db_manipulations import viewer_only
from Smartscope.core.cache import save_json_from_cache
from Smartscope.core.models import *
from Smartscope.core.settings.worker import PLUGINS_FACTORY
from Smartscope.core.main_commands import check_pause

logger = logging.getLogger(__name__)


def image_as_bytes(image_path):
    img = Path(image_path)
    return open(img,'rb'), img.name

def svg_as_png(instance, context):
    d = instance.svg(display_type=context['display_type'], method=context['method'])
    scale = min([1000/d.width, 1000/d.height])
    d.set_pixel_scale(scale)
    d.save_png('/tmp/download.png')
    with  open('/tmp/download.png','rb') as f:
        img = io.BytesIO(f.read())

    return img, f'{instance.name}.png'

class GeneralActionsMixin:

    @action(detail=False, methods=['post'])
    def delete_many(self,request):
        logger.debug('Received delete_many request')
        logger.debug(request.data)
        queryset = self.queryset.filter(pk__in=request.data)
        logger.debug(queryset)
        queryset.delete()
        return Response(status=rest_status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def post_many(self, request, *args, **kwargs):
        logger.debug('Received post_many request')
        logger.debug(request.data)
        serializer = self.get_serializer(data=request.data, many=True)
        try:
            if serializer.is_valid():
                logger.debug(f'Valid!')
                objs = serializer.create(serializer.validated_data)
            logger.debug(f'Created {len(objs)} objects')
            headers = self.get_success_headers(serializer.data)
            output = self.get_serializer(data=objs,many=True)
            output.is_valid()
            return Response(data=output.data, status=rest_status.HTTP_201_CREATED)
        except Exception as err:
            logger.exception(f'Error while posting many, {err}.')
            return Response(serializer.errors, status=rest_status.HTTP_400_BAD_REQUEST)
        
class ExtraActionsMixin:

    def load(self, request, **kwargs):
        obj = self.queryset.filter(pk=kwargs['pk']).first()
        serializer = SvgSerializer(instance=obj, context={'request': request})
        context = serializer.data
        return Response(serializer.data, template_name='mapcard.html')
    
    def get_card_context(self,instance,request,**kwargs):
        context = {
            'instance': instance,
            'targets_methods': targets_methods(instance),
            'display_type': get_request_param(request, 'display_type', 'classifiers'),
            'method': get_request_param(request, 'method'),
            'TRAINING_ANNOTATOR_FEATURE_FLAG': settings.TRAINING_ANNOTATOR_FEATURE_FLAG,
        }
        if context['method'] is None:
            methods = context['targets_methods'].get(context['display_type'], [])
            if len(methods) > 0:
                context['method'] = methods[0].name
        return context

    def load_card(self, request, **kwargs):
        reset_queries()
        obj = self.queryset.filter(pk=kwargs['pk']).first()
        context = self.get_card_context(obj, request)
        serializer = SvgSerializer(instance=obj, display_type=context['display_type'], method=context['method'])
        context = {**context, **serializer.data}
        context['card'] = render_to_string('mapcard.html', context=context, )
        logger.debug(f"{context['method']}, {context['display_type']}")
        logger.debug(f'Loading card required {len(connection.queries)} queries')
        return Response(dict(card=context['card'], displayType=context['display_type'], method=context['method'])) #fullmeta=context['fullmeta'],

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
            'mrc': functools.partial(image_as_bytes,instance.mrc),
            'raw': functools.partial(image_as_bytes,instance.raw_mrc),
            'png': functools.partial(image_as_bytes,instance.png),
            'svg': functools.partial(svg_as_png, instance, self.get_card_context(instance,request))
        }
        img,name = extension_factory[extension]()
        response = FileResponse(img, content_type='image/*', as_attachment=True, filename=name)
        return response




class TargetRouteMixin:

    detailed_serializer = None

    def get_detailed_serializer(self, serializer=None):
        if serializer is not None:
            return serializer
        if self.detailed_serializer is None:
            raise ValueError(f'detailed_serializer attribute is not set on {self.__class__.__name__}.')
        return self.detailed_serializer

    @ action(detail=True, methods=['get','patch'], url_path='detailed')
    def detailedOne(self, request, *args, **kwargs):
        self.serializer_class = self.get_detailed_serializer()
        if request.method == 'PATCH':
            return self.detailed_patch(request=request, *args, **kwargs)

        obj = self.get_object()
        serializer = self.get_serializer(obj, many=False)
        return Response(data=serializer.data)

    @ action(detail=False, methods=['get'], url_path='detailed')
    def detailedMany(self, request, *args, serializer=None, **kwargs):
        self.serializer_class = self.get_detailed_serializer(serializer)
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['post', 'patch'])
    def post_detailedMany(self, request, *args, **kwargs):
        self.serializer_class = self.get_detailed_serializer()
        serializer = self.get_serializer(data=request.data, many=True)
        if serializer.is_valid():
            logger.debug(f'Valid!')
            serializer.save()
            self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @ action(detail=False, methods=['get'], url_path='scipion_plugin')
    def scipion_plugin(self, request, *args, **kwargs):
        return self.detailedMany(request=request,*args,serializer=ScipionPluginHoleSerializer ,**kwargs)

    @action(detail=False, methods=['post'])
    def add_targets(self, request, *args, **kwargs):
        logger.debug(f'Received create_targets request with params: {request.query_params}')
        self.serializer_class = self.get_detailed_serializer()
        serializer = self.get_serializer(data=request.data, many=True)
        label_types = request.query_params.get('label_types', '__all__').split(',')
        try:
            logger.debug(request.data[0])
            if serializer.is_valid(raise_exception=True):
                logger.debug(f'Valid!')
                objs, labels = serializer.create(request.data, label_types=label_types)
                logger.debug(f'Created {len(objs)} objects')
                with transaction.atomic():
                    objs = [obj.save() for obj in objs]
                    [label.save() for label in labels]
                outputs = self.get_serializer(instance=objs, many=True)
                # outputs.is_valid(raise_exception=True)
                logger.debug(f'Ouputs:\n{outputs.data}')
                return Response(data=outputs.data, status=rest_status.HTTP_201_CREATED)
            serializer.errors()
        except Exception as err:
            logger.exception(f'Error while posting many, {err}.')
            return Response(serializer.errors, status=rest_status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['patch'])    
    def update_many(self,request, *args, **kwargs):
        logger.debug('Received update_many request')
        logger.debug(request.data)
        data = request.data.copy()
        uids = data.pop('uids')
        objs = self.queryset.filter(pk__in=uids)
        try:
            with transaction.atomic():
                for obj in objs:
                    for key, value in data.items():
                        setattr(obj, key, value)
                    obj.save()
            return Response(status=rest_status.HTTP_200_OK)
        except Exception as err:
            logger.exception(f'Error while updating many, {err}.')
            return Response(err, status=rest_status.HTTP_400_BAD_REQUEST)
        
    def detailed_patch(self,request,*args,**kwargs):
        return self.partial_update(request, *args, **kwargs)

          

class UserViewSet(viewsets.ModelViewSet, GeneralActionsMixin,):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class GroupViewSet(viewsets.ModelViewSet, GeneralActionsMixin,):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAdminUser]


class MicroscopeViewSet(viewsets.ModelViewSet, GeneralActionsMixin,):
    """
    API endpoint that allows ScreeningSessions to be viewed or edited.
    """
    queryset = Microscope.objects.all()
    serializer_class = MicroscopeSerializer
    permission_classes = [permissions.IsAuthenticated]


class DetectorViewSet(viewsets.ModelViewSet, GeneralActionsMixin,):
    """
    API endpoint that allows ScreeningSessions to be viewed or edited.
    """
    queryset = Detector.objects.all()
    serializer_class = DetectorSerializer
    permission_classes = [permissions.IsAuthenticated]

    filterset_fields = ['id', 'microscope_id', 'name']


class GridCollectionParamsViewSet(viewsets.ModelViewSet, GeneralActionsMixin,):
    """
    API endpoint that allows ScreeningSessions to be viewed or edited.
    """
    queryset = GridCollectionParams.objects.all()
    serializer_class = GridCollectionParamsSerializer
    permission_classes = [permissions.IsAuthenticated]

class ScreeningSessionsViewSet(viewsets.ModelViewSet, GeneralActionsMixin,):
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
                send_to_worker(
                    self.object.microscope_id.worker_hostname,
                    self.object.microscope_id.executable,
                    arguments=['autoscreen', self.object.session_id],
                )
            else:
                logger.info('stopping')
                send_to_worker(
                    self.object.microscope_id.worker_hostname,
                    self.object.microscope_id.executable,
                    arguments=['stop_session', self.object.session_id]
                )

            rounds = 0
            check = True
            while check:
                logger.info('Starting checks')
                rounds += 1
                if rounds > 15:
                    return Response({
                        'error': 'Command Timeout reached',
                        'isRunning': process.status == 'running',
                        'pid': process.PID,
                        'status': process.status
                    })
                time.sleep(1)
                process = self.object.process_set.first()
                if process_init is None:
                    if process_init != process:
                        check = False
                else:
                    if process_init.status != process.status:
                        check = False

            return Response({
                'isRunning': process.status == 'running',
                'pid': process.PID,
                'status': process.status
            })

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
            out = out.decode("utf-8").strip().split('\n')[-1]
            return Response(json.loads(out))

    @ action(detail=True, methods=['put'])
    def continue_run(self, request, **kwargs):
        self.object = self.get_object()
        data = request.data
        if 'continue' in data.keys():
            out, err = send_to_worker(self.object.microscope_id.worker_hostname, self.object.microscope_id.executable,
                                      arguments=['continue_run', data['continue'], self.object.microscope_id.pk], communicate=True)
            out = out.decode("utf-8").strip().split('\n')[-1]
            return Response(json.loads(out))

    @ action(detail=True, methods=['get'])
    def get_logs(self, request, **kwargs):
        self.object = self.get_object()
        logger.info('Fetching logs')
        # check_output, err = send_to_worker(self.object.microscope_id. worker_hostname,
                                        #    self.object.microscope_id.executable, arguments=['check_pause', self.object.microscope_id.pk, self.object.session_id], communicate=True)
        # logger.debug(f'Check pause output: {check_output}')
        # check_output = json.loads(check_output.decode("utf-8").strip().split('\n')[-1])
        check_output = check_pause(self.object.microscope_id.pk, self.object.session_id)
        disk_status = disk_space(settings.AUTOSCREENDIR)
        out = self.read_file('run.out')
        proc = self.read_file('proc.out')
        # queue = self.read_file('queue.txt', start_line=0)

        return Response(dict(out=out, proc=proc, disk=disk_status, **check_output))

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


class MeshMaterialViewSet(viewsets.ModelViewSet, GeneralActionsMixin,):
    """
    API endpoint that allows Mesh Material to be viewed or edited.
    """
    queryset = MeshMaterial.objects.all()
    serializer_class = MeshMaterialSerializer
    permission_classes = [permissions.IsAuthenticated]


class MeshSizeViewSet(viewsets.ModelViewSet, GeneralActionsMixin,):
    """
    API endpoint that allows Mesh Sizes to be viewed or edited.
    """
    queryset = MeshSize.objects.all()
    serializer_class = MeshSizeSerializer
    permission_classes = [permissions.IsAuthenticated]


class HoleTypeViewSet(viewsets.ModelViewSet, GeneralActionsMixin,):
    """
    API endpoint that allows Hole types to be viewed or edited.
    """
    queryset = HoleType.objects.all()
    serializer_class = HoleTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

def get_queue(grid):
    square = grid.squaremodel_set.filter(selected=True).\
        exclude(status__in=[status.SKIPPED, status.COMPLETED]).\
        order_by('number').first()
    hole = grid.holemodel_set.filter(selected=True, square_id__status=status.COMPLETED).\
        exclude(status__in=[status.SKIPPED, status.COMPLETED]).\
        order_by('square_id__completion_time', 'number').first()
    return square, hole

class AutoloaderGridViewSet(viewsets.ModelViewSet, GeneralActionsMixin, ExtraActionsMixin):
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
        data['squares'] = [] #list_to_dict(data['squares'])
        data['holes'] = []
        # data['counts'] = get_hole_count(obj)
        return Response(data)

    @ action(detail=True, methods=['patch'])
    def editcollectionparams(self, request, **kwargs):
        obj = self.get_object()
        data = request.data
        logger.debug(data)
        try:
            form_params = GridCollectionParamsForm(data)
            if form_params.is_valid():
                multishot_per_hole_id = form_params.cleaned_data.pop('multishot_per_hole_id')
                # preprocessing_pipeline_id = form_params.cleaned_data.pop('preprocessing_pipeline_id')
                if multishot_per_hole_id != "":
                    save_json_from_cache(multishot_per_hole_id, obj.directory,'multishot')
                # if preprocessing_pipeline_id != "":
                #     save_json_from_cache(preprocessing_pipeline_id,obj.directory,'preprocessing')
                params, created = GridCollectionParams.objects.get_or_create(**form_params.cleaned_data)
                logger.debug(f'Params newly created: {created}')
                obj.params_id = params
                obj.save()
                return Response(dict(success=True))
            else:
                logger.debug(f'Form invalid , {form_params}.')
                return Response(dict(success=False))
        except Exception as err:
            logger.exception(f'Error while updating parameters, {err}.')
            return Response(dict(success=False))

    @ action(detail=True, methods=['get'])
    def export(self, resquest, **kwargs):
        obj = self.get_object()
        self.serializer_class = ExportMetaSerializer
        serializer = self.get_serializer(obj, many=False)
        return Response(data=serializer.data)
    

    @action(detail=True, methods=['get'])
    def get_queue(self,request, **kwargs):
        obj = self.get_object()
        if obj is None:
            return Response({'error': f'Grid {obj} not found'}, status=404)
        
        square, hole = get_queue(obj)
        
        # Serialize the data if needed
        square_data = DetailedFullSquareSerializer(square).data if square else None
        hole_data = DetailedFullHoleSerializer(hole).data if hole else None
        
        return Response({'squaremodel': square_data, 'holemodel': hole_data})
    
    @ action(detail=True, methods=['patch'], url_path='regroup_bis')
    def regroup_bis(self, request, *args, **kwargs):
        try:
            obj = self.get_object()
            microscope = obj.session_id.microscope_id
            out, err = send_to_worker(microscope.worker_hostname, microscope.executable, arguments=[
                'regroup_bis', obj.pk, 'all'], communicate=True, timeout=30)
            out = out.decode("utf-8").strip().split('\n')[-1]
            return Response(dict(out=out))
        except Exception as err:
            logger.error(f'Error tring to regrouping BIS, {err}')
            return Response(dict(success=False),status=rest_status.HTTP_500_INTERNAL_SERVER_ERROR)  

    @ action(detail=True, methods=['patch'])
    def regroup_and_reselect(self, request, *args, **kwargs):
        try:
            obj = self.get_object()
            microscope = obj.session_id.microscope_id
            out, err = send_to_worker(microscope.worker_hostname, microscope.executable, arguments=[
                'regroup_bis_and_select', obj.pk, 'all'], communicate=True, timeout=120)
            out = out.decode("utf-8").strip().split('\n')[-1]
            return Response(dict(out=out))
        except Exception as err:
            logger.error(f'Error tring to regrouping BIS and reselecting, {err}')
            return Response(dict(success=False),status=rest_status.HTTP_500_INTERNAL_SERVER_ERROR)

    @ action(detail=True, methods=['get'])
    def get_report_url(self, request, *args, **kwargs):
        obj:AutoloaderGrid = self.get_object()
        url=  request.build_absolute_uri(reverse('browser') + f'?group={obj.session_id.group.pk}&session_id={obj.session_id.pk}&grid_id={obj.pk}')
        return Response(url)


class AtlasModelViewSet(viewsets.ModelViewSet, GeneralActionsMixin, ExtraActionsMixin, TargetRouteMixin):
    """
    API endpoint that allows Atlases to be viewed or edited.
    """
    queryset = AtlasModel.objects.all()
    serializer_class = AtlasSerializer
    detailed_serializer = DetailedFullAtlasSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType',
                        'grid_id__meshSize', 'grid_id__quality', 'grid_id__session_id', 'status']

    @ action(detail=True, methods=['get'])
    def load(self, request, **kwargs):
        return super().load_card(request, **kwargs)


class SquareModelViewSet(viewsets.ModelViewSet, GeneralActionsMixin, ExtraActionsMixin, TargetRouteMixin):
    """
    API endpoint that allows Squares to be viewed or edited.
    """
    queryset = SquareModel.objects.all()
    serializer_class = SquareSerializer
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType', 'grid_id__meshSize', 'grid_id__quality',
                        'atlas_id', 'selected', 'grid_id__session_id', 'status']
    detailed_serializer = DetailedFullSquareSerializer

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
                status = 'queued'
            elif action == 'cancelall':
                query = obj.holemodel_set.filter(status='queued').update(selected=False,status=None)

            with transaction.atomic():
                for target in query:
                    target.selected = selected
                    target.status = status
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
        
    @ action(detail=True, methods=['delete'])
    def delete_holes(self,request, *args, **kwargs):
        logger.debug('Received delete_holes request')
        obj = self.get_object()
        data = request.data
        logger.debug(data)
        queryset = obj.holemodel_set.filter(status__isnull=True, selected=False)
        logger.debug(f"Deleting {queryset.count()} holes")
        queryset.delete()
        return Response(data=dict(success=True),status=rest_status.HTTP_204_NO_CONTENT)
    
    @ action(detail=True, methods=['get'])
    def extend_lattice(self,request, *args, **kwargs):
        obj = self.get_object()
        logger.debug(f'Extending lattice for square {obj}')
        microscope = obj.grid_id.session_id.microscope_id
        out, err = send_to_worker(microscope.worker_hostname, microscope.executable, arguments=[
            'extend_lattice', obj.square_id], communicate=True, timeout=30)
        out = out.decode("utf-8").strip().split('\n')[-1]
        return Response(data=json.loads(out), content_type='application/json')



class HoleModelViewSet(viewsets.ModelViewSet, GeneralActionsMixin, ExtraActionsMixin, TargetRouteMixin):
    """
    API endpoint that allows Squares to be viewed or edited.
    """
    queryset = HoleModel.objects.all()
    serializer_class = HoleSerializer
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType', 'grid_id__meshSize', 'grid_id__quality', 'grid_id__session_id',
                        'square_id', 'status', 'bis_group', 'bis_type']

    detailed_serializer = DetailedFullHoleSerializer

    @ action(detail=True, methods=['get'])
    def load(self, request, **kwargs):
        return super().load_card(request, **kwargs)

    @ action(detail=False, methods=['get'])
    def simple(self, request, *args, **kwargs):
        self.serializer_class = HoleSerializerSimple
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @ action(detail=True, methods=['get'])
    def highmag(self, request, *args, **kwargs):
        obj = self.get_object()
        self.renderer_classes = [TemplateHTMLRenderer]

        if obj.bis_group is None:
            queryset = list(HighMagModel.objects.filter(hole_id=kwargs['pk'], status='completed'))
        else:
            queryset = list(HighMagModel.objects.filter(grid_id=obj.grid_id,
                                                        hole_id__bis_group=obj.bis_group, status='completed').order_by('hole_id__number','number'))
        context = {}
        context['classifier'] = PLUGINS_FACTORY.get_plugin('Micrographs curation')
        response_context= dict(cards=[])
        for hole in queryset:
            context['hole']=hole
            context['svg'] = hole.svg().as_svg()
            response_context['cards'].append(render_to_string('holecard.html',context))
        resp = SimpleTemplateResponse(context=response_context, content_type='text/html', template='holecards.html')
        logger.debug(resp)
        return resp

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


class HighMagModelViewSet(viewsets.ModelViewSet, GeneralActionsMixin, ExtraActionsMixin, TargetRouteMixin):
    """
    API endpoint that allows Atlases to be viewed or edited.
    """
    queryset = HighMagModel.objects.all()
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    serializer_class = HighMagSerializer
    filterset_fields = ['grid_id', 'grid_id__meshMaterial', 'grid_id__holeType', 'grid_id__meshSize',
                        'grid_id__quality', 'hole_id', 'hole_id__square_id', 'grid_id__session_id', 'hm_id', 'number', 'status','name','frames']

    detailed_serializer = DetailedHighMagSerializer

    @ action(detail=True, methods=['patch'])
    def upload_images(self,request, *args, **kwargs):
        
            allowed_keys = ['mrc','png','ctf_img']
            obj = self.get_object()
            data = request.data
            has_errors = False
            has_success = False
            return_data = dict()
            logger.debug(data.keys())
            for key,image in data.items():
                if key not in allowed_keys:
                    message = f"Key: {key} is not valid, choose from {', '.join(allowed_keys)}"
                    return_data[key] = message
                    has_errors = True
                    logger.warning(message)
                    continue
                try:
                    file = io.BytesIO(base64.b64decode(image))
                    #Validate image while in memory
                    filepath = getattr(obj,key)
                    logger.info(f'Saving {obj.name} -> {key} image to {filepath}')
                    with open(filepath, "wb") as f:
                        f.write(file.getbuffer())
                    message = f'Key: {key}, successfully uploaded and saved.'
                    return_data[key] = message
                    logger.info(message)
                    has_success = True
                except Exception as err:
                    has_errors = True
                    message = f'Key: {key}, an error occured: {err}. Check smartscope.log for more details'
                    logger.info(message)
                    return_data[key] = message
                    logger.exception(err)
            logger.info('Done uploading images.')
            if not has_errors and has_success:
                return Response(status=200, data=return_data)
            if has_errors and has_success:
                return Response(status=207, data=return_data)
            if has_errors and not has_success:
                return Response(status=200, data=return_data)


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
    

class ClassifierViewSet(viewsets.ModelViewSet):
    queryset = Classifier.objects.all()
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    serializer_class = ClassifierSerializer
    filterset_fields = ['object_id','method_name','content_type']

    detailed_serializer = DetailedHighMagSerializer 