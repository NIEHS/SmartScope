import os
import json
import subprocess as sub
import psutil
from datetime import datetime
import logging
import plotly.graph_objs as go


from django.shortcuts import render
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.template.response import TemplateResponse
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.utils.timezone import now

from .forms import *
from Smartscope.core.db_manipulations import viewer_only
from Smartscope.core.stats import get_hole_count
from Smartscope.core.protocols import get_or_set_protocol
from Smartscope.core.grid.grid_io import GridIO
from Smartscope.lib.record_params import RecordParams
from Smartscope.lib.multishot import set_shots_per_hole
from Smartscope.core.grid.run_hole import RunHole
from Smartscope.core.cache import save_json_from_cache
from Smartscope.core.protocols import load_protocol, set_protocol
from Smartscope.core.preprocessing_pipelines import PREPROCESSING_PIPELINE_FACTORY, load_preprocessing_pipeline

from Smartscope.core.models.grid import AutoloaderGrid
from Smartscope.core.models.grid_collection_params import GridCollectionParams
from Smartscope.core.models.screening_session import ScreeningSession


logger =logging.getLogger(__name__)

def signup(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('/grid_inventory/grid_selection')
    else:
        form = UserCreateForm()
    return render(request, 'grid_inventory/signup.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))


class AutoScreenViewer(LoginRequiredMixin, TemplateView):
    template_name = "autoscreenViewer/auto_screen_viewer.html"
    login_url = '/login'
    redirect_field_name = 'redirect_to'

class AutoScreenSetup(LoginRequiredMixin, TemplateView):
    template_name = "smartscopeSetup/run_setup.html"
    login_url = '/login'
    redirect_field_name = 'redirect_to'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not 'form_general' in kwargs.keys():
            form_general = ScreeningSessionForm()
            form_params = GridCollectionParamsForm()
            form_preprocess = PreprocessingPipelineIDForm()
        else:
            form_general = kwargs['form_general']
            form_params = kwargs['form_params']
            form_preprocess = kwargs['form_preprocess']

        grids = []
        form = AutoloaderGridForm(prefix=1)
        form.fields['position'].initial = 1

        grids.append(form)

        context = dict(form_general=form_general, form_params=form_params,form_preprocess=form_preprocess, grids=grids)
        sessions = ScreeningSession.objects.all().order_by('-date')[:10]
        context['sessions'] = sessions
        return context

    def post(self, request, **kwargs):
        is_viewer_only = viewer_only(self.request.user)
        form_general = ScreeningSessionForm(request.POST)
        form_params = GridCollectionParamsForm(request.POST)
        form_preprocess = PreprocessingPipelineIDForm(request.POST)
        if not is_viewer_only:
            num_grids = set([k.split('-')[0] for k in request.POST.keys() if k.split('-')[0].isnumeric()])

            if form_general.is_valid() and form_params.is_valid() and form_preprocess.is_valid():

                session, created = ScreeningSession.objects.get_or_create(
                    **form_general.cleaned_data,
                    date=datetime.today().strftime('%Y%m%d')
                )
                if created:
                    logger.debug(f'{session} newly created')

                # multishot = form_params.cleaned_data.pop('multishot_per_hole')
                multishot_per_hole_id = form_params.cleaned_data.pop('multishot_per_hole_id')
                preprocessing_pipeline_id = form_preprocess.cleaned_data.pop('preprocessing_pipeline_id',False)
                params, created = GridCollectionParams.objects.get_or_create(**form_params.cleaned_data)
                if created:
                    logger.debug(f'{params} newly created')

                for i in num_grids:
                    form = AutoloaderGridForm(request.POST, prefix=i)
                    if form.is_valid():
                        if form.cleaned_data['name'] != '':
                            protocol = form.cleaned_data.pop('protocol')
                            grid, created = AutoloaderGrid.objects.get_or_create(
                                **form.cleaned_data, session_id=session, params_id=params)
                            
                            if created:
                                logger.debug(f'{grid} newly created, creating directories')
                                GridIO.create_grid_directories(grid.directory)
                            else:
                                logger.debug(f'{grid} exists')
                            logger.debug(f'Setting protocol {protocol} for {grid}')
                            get_or_set_protocol(grid,protocol)
                            if params.multishot_per_hole:
                                save_json_from_cache(multishot_per_hole_id, grid.directory,'multishot')
                            if preprocessing_pipeline_id != '':
                                save_json_from_cache(preprocessing_pipeline_id, grid.directory,'preprocessing')

                return redirect(f'../session/{session.session_id}')

        context = self.get_context_data(form_general=form_general, form_params=form_params)

        return render(request, self.template_name, context)


class AutoScreenRun(LoginRequiredMixin, TemplateView):
    template_name = "autoscreenViewer/run_session.html"
    login_url = '/login'
    redirect_field_name = 'redirect_to'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alive = False
        to_reload = False
        if 'session_id' in kwargs:
            self.session = ScreeningSession.objects.get(session_id=kwargs['session_id'])
            self.working_dir = self.session.directory
            context['session'] = self.session
            try:
                process = Process.objects.get(session_id=self.session.session_id)
                if process.status == 'Running':
                    alive, to_reload = self.check_status(process)
            except Process.DoesNotExist:
                process = None

            context['process'] = process
            context['alive'] = alive
            context['reload'] = to_reload

        sessions = ScreeningSession.objects.all().order_by('-date')[:10]
        context['sessions'] = sessions

        return context

    def post(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        proc = context['process']
        body = json.loads(request.body)
        if 'start' in body:
            logger.debug('starting process')
            pid = self.start_process()
            if proc is None:
                proc = Process(session_id=context['session'], PID=pid, status='Running')
            else:
                proc.PID = pid
                proc.status = 'Running'
            proc.save()
        return JsonResponse(dict(status='yay!'))

    def put(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        body = json.loads(request.body)
        if 'start' in body:
            logger.debug('Stop process')
            self.stop_process(context['process'])
            return JsonResponse(dict(status='yay!'))

        if 'pause' in body:
            pause_file = os.path.join(os.getenv('MOUNTLOC'), '.pause')
            if os.path.isfile(pause_file):
                os.remove(pause_file)
                return JsonResponse(dict(pause=False))
            else:
                open(pause_file, 'w').close()
                return JsonResponse(dict(pause=True))

        if 'continue' in body:
            value = body['continue']
            if value == 'next':
                open(os.path.join(os.getenv('MOUNTLOC'), 'next'), 'w').close()
            os.remove(os.path.join(os.getenv('MOUNTLOC'), 'paused'))
            return JsonResponse(dict(paused=value))

    def get(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        if 'getarg' in kwargs:
            if kwargs['getarg'] == 'logs':
                logger.debug('GOT REQUEST!')
                pause = os.path.isfile(os.path.join(os.getenv('MOUNTLOC'), '.pause'))
                paused = os.path.isfile(os.path.join(os.getenv('MOUNTLOC'), 'paused'))
                try:
                    out = self.read_file('run.out')
                    err = self.read_file('run.err')
                    queue = self.read_file('queue.txt')
                except FileNotFoundError:
                    out = ''
                    err = ''
                    queue = ''

                return JsonResponse(dict(out=out, err=err, queue=queue, reload=context['reload'], pause=pause, paused=paused))

        return render(request, self.template_name, context)

    def read_file(self, name):
        try:
            with open(os.path.join(self.working_dir, name), 'r') as f:
                file = f.read()
            return file
        except FileNotFoundError:
            return ''

    def start_process(self):
        logger.debug(' '.join(['nohup', 'python',
            os.path.join(settings.BASE_DIR, 'autoscreen.py'),
            self.session.session_id])
        )
        proc = sub.Popen(['nohup', 'python',
            os.path.join(settings.BASE_DIR, 'autoscreen.py'),
            self.session.session_id],
            stdin=None, stdout=None, stderr=None, preexec_fn=os.setpgrp)
        return proc.pid

    def stop_process(self, process):
        sub.run(['kill', str(process.PID)])
        process.status = 'Stopped'
        process.end_time = now()
        process.save()

    def check_status(self, process):
        to_reload = False
        try:
            proc = psutil.Process(process.PID)
        except psutil.NoSuchProcess:
            return False, to_reload
        is_running = proc.is_running()
        logger.debug('Is_running: ', is_running)
        logger.debug('status: ', proc.status())
        if len(self.read_file('run.err')) > 0 and is_running is False:
            process.status = 'Error'
            process.end_time = now()
            process.save()
            to_reload = True
        elif process.status == 'Running' and is_running is False:
            process.status = 'Finished'
            process.end_time = now()
            process.save()
            to_reload = True
        elif process.status == 'Running' and proc.status() == 'zombie':
            process.status = 'Killed'
            process.end_time = now()
            process.save()
            to_reload = True

        return is_running, to_reload


class EvaluateMicrographs(LoginRequiredMixin, TemplateView):
    template_name = "autoscreenViewer/micrograph_evaluation.html"
    login_url = '/login'
    redirect_field_name = 'redirect_to'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['quality_choices'] = HoleModel.QUALITY_CHOICES

        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)

class MultiShotView(TemplateView):
    template_name = 'smartscopeSetup/multishot/multishot.html'
    results_template = 'smartscopeSetup/multishot/multishot_results.html'
    login_url = '/login'
    redirect_field_name = 'redirect_to'

    def get_context_data(self,grid_id,**kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SetMultiShotForm()
        context['current'] = None
        if grid_id is not None:
            grid = AutoloaderGrid.objects.get(grid_id=grid_id)
            mutlishot_file = Path(grid.directory,'multishot.json')
            multishot = RunHole.load_multishot_from_file(mutlishot_file)
            context['current'] = multishot
            logger.debug(f'MultiShotViewGrid with {grid_id}')
        return context
    
    def get(self,request, *args, grid_id=None, **kwargs):
        context = self.get_context_data(grid_id=grid_id,**kwargs)

        return render(request,self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        try:
            form = SetMultiShotForm(request.POST)

            if form.is_valid(): 
                logger.debug(form.cleaned_data)
                data=form.cleaned_data
                max_shots = data.pop('max_number_of_shots')
                max_efficiency = data.pop('max_efficiency') / 100
                params = RecordParams(**data)
                results = []
                for n_shots in range(1,max_shots):
                    shot = set_shots_per_hole(number_of_shots=n_shots+1,
                                                hole_size=params.hole_size,
                                                beam_size=params.beam_size_um,
                                                image_size=params.detector_size_um,
                                                min_efficiency=max_efficiency)
                    if shot is None:
                        continue
                    shot.set_display(params)
                    cache.set(shot.cache_id,shot.json(exclude={'cache_id'}),timeout=30*60)
                    results.append(shot) 
                logger.debug(results)
                context={'results':results}
                      
                return render(request,template_name=self.results_template,context=context)  
            
            return HttpResponse("<div>INVALID!</div>")
        except Exception as err:
            logger.exception(err)
            return HttpResponse(f"<div>{err}</div>")
        
class ProtocolView(TemplateView):
    template_name = "autoscreenViewer/protocol.html"

    def get_context_data(self, grid_id, **kwargs):
        context = super().get_context_data(**kwargs)
        grid= AutoloaderGrid.objects.get(pk=grid_id)
        protocol = load_protocol(file=grid.protocol)
        context['grid'] = grid
        context['protocol'] = protocol
        context['protocolDetails'] = yaml.dump(context['protocol'].dict())
        context['form'] = SelectProtocolForm(dict(protocol=protocol.name))
        return context
    
    def get(self,request, grid_id, *args, **kwargs):
        context = self.get_context_data(grid_id, **kwargs)
        return render(request,self.template_name, context)    
    
    def post(self, request, grid_id, *args, **kwargs):
        context = self.get_context_data(grid_id, **kwargs)
        try:
            form = SelectProtocolForm(request.POST)
            if form.is_valid(): 
                logger.debug(form.cleaned_data)
                data=form.cleaned_data
                protocol = set_protocol(data['protocol'],context['grid'].protocol)
                context = self.get_context_data(grid_id, **kwargs)
                context['success'] = True
                return render(request,self.template_name, context) 
            return HttpResponse("<div>INVALID!</div>")
        except Exception as err:
            logger.exception(err)
            return HttpResponse(f"<div>{err}</div>")  
        
class MicroscopeStatus(TemplateView):
    template_name= "autoscreenViewer/microscopes_status.html"

    def get_context_data(self,*args, **kwargs):
        context = super().get_context_data(**kwargs)
        microscopes = Microscope.objects.all()
        context['microscopes'] = microscopes
        return context
    
    def get(self,request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        return render(request,self.template_name, context)
    
class PreprocessingPipeline(TemplateView):
    template_name= "smartscopeSetup/preprocessing/preprocessing_pipeline.html"

    def get(self,request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request,self.template_name, context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SelectPeprocessingPipilelineForm()
        return context
    
    def get_grid_context_data(self,grid_id):
        context = dict()
        grid = AutoloaderGrid.objects.get(pk=grid_id)
        pipeline_data = load_preprocessing_pipeline(Path(grid.directory, 'preprocessing.json'))
        pipeline = PREPROCESSING_PIPELINE_FACTORY[pipeline_data.pipeline]
        context['grid'] = grid
        context['form'] = SelectPeprocessingPipilelineForm(data={'pipeline':pipeline_data.pipeline})
        context['pipeline_form'] = pipeline.form(data=pipeline_data.kwargs)
        context['pipeline'] = pipeline_data.pipeline
        context['description'] = pipeline.description
        context['pipeline_data'] = pipeline_data
        return context

    def get_grid_pipeline(self, request, *args ,grid_id, **kwargs):
        context = self.get_grid_context_data(grid_id)
        return render(request,self.template_name, context)

    
    def get_pipeline(self, request, *args, **kwargs,):
        try:
            context = {}
            pipeline = request.GET.get('pipeline',None)
            # form = SelectPeprocessingPipilelineForm(request.POST)
            # is_valid = form.is_valid()
            # if not is_valid:
            #     return HttpResponse('Form invalid')
            # if is_valid: 
            #     logger.debug(form.cleaned_data)
            #     data = form.cleaned_data
            pipeline_obj = PREPROCESSING_PIPELINE_FACTORY[pipeline]
            logger.debug(pipeline)
            context['pipeline'] = pipeline
            context['description'] = pipeline_obj.description
            context['form'] = pipeline_obj.form()
            # context['grid_id'] = None
            return TemplateResponse(request=request,template="smartscopeSetup/preprocessing/preprocessing_pipeline_form.html",context=context)
        except Exception as err:
            logger.exception(err)
    
    def set_pipeline(self, request,pipeline, *args, grid_id=None, **kwargs):
        try:
            logger.debug(request.POST)
            pipeline_obj = PREPROCESSING_PIPELINE_FACTORY[pipeline]
            form = pipeline_obj.form(request.POST)
            logger.debug(f'Updating pipeline for {grid_id}')
            if form.is_valid():
                pipeline_data = pipeline_obj.pipeline_data(form.cleaned_data)
                if grid_id is None or not grid_id:
                    cache.set(pipeline_data.cache_id,pipeline_data.json(exclude={'cache_id'}),timeout=30*60)
                    logger.debug(pipeline_data)
                    return TemplateResponse(request=request,
                                            template='forms/formFieldsBase.html',
                                            context=dict(form=PreprocessingPipelineIDForm(data=dict(preprocessing_pipeline_id=pipeline_data.cache_id)), 
                                                                                        row=True, 
                                                                                        id='formPreprocess'))
                grid = AutoloaderGrid.objects.get(pk=grid_id)
                Path(grid.directory,'preprocessing.json').write_text(pipeline_data.json(exclude={'cache_id'}))
                logger.info('Updated pipeline for existing grid')
                return self.get_grid_pipeline(request, grid_id=grid_id)
        except Exception as err:
            logger.exception(err)

    def start(self, request, grid_id, *args, **kwargs):
        context = self.get_grid_context_data(grid_id)
        context['pipeline_data'].start(context['grid'])
        return self.get_grid_pipeline(request,grid_id=grid_id)

    def stop(self, request, grid_id, *args, **kwargs):
        context = self.get_grid_context_data(grid_id)
        context['pipeline_data'].stop(context['grid'])
        return self.get_grid_pipeline(request,grid_id=grid_id)

class CollectionStatsView(TemplateView):
    template_name = "autoscreenViewer/collection_stats.html"

    def ctfGraph(self,grid_id):
        ### NEED TO MOVE THE GRAPHING LOGIC OUTSIDE OF HERE
        data = list(HighMagModel.objects.filter(status='completed', grid_id=grid_id, ctffit__lte=15).values_list('ctffit', flat=True)) # replace with your own data source
        hist = go.Histogram(x=data, nbinsx=30)
        layout = go.Layout(
                            title='CTF fit distribution',
                            xaxis=dict(
                                title='CTF fit resolution (Angstrom)'
                            ),
                            yaxis=dict(
                                title='Number of exposures'
                            ),
                            showlegend=False,
                        )
        fig = go.Figure(data=[hist],layout=layout,)
        graph = fig.to_html(full_html=False)
        return graph


    def get_context_data(self, grid_id, **kwargs):
        context = super().get_context_data(**kwargs)
        grid= AutoloaderGrid.objects.get(pk=grid_id)
        context.update(get_hole_count(grid))
        context['graph'] = self.ctfGraph(grid_id)
        return context
    
    def get(self,request, grid_id, *args, **kwargs):
        context = self.get_context_data(grid_id, **kwargs)
        return render(request,self.template_name, context)   