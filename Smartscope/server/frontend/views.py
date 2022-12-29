from django.shortcuts import render
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.shortcuts import redirect
import os
import json
from .forms import *
import subprocess as sub
import psutil
from django.utils.timezone import now
from Smartscope.core.db_manipulations import viewer_only
from Smartscope.lib.file_manipulations import create_grid_directories
from Smartscope.core.protocols import get_protocol
from datetime import datetime


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
    template_name = "autoscreenViewer/run_setup.html"
    login_url = '/login'
    redirect_field_name = 'redirect_to'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not 'form_general' in kwargs.keys():
            form_general = ScreeningSessionForm()
            form_params = GridCollectionParamsForm()
        else:
            form_general = kwargs['form_general']
            form_params = kwargs['form_params']

        grids = []
        form = AutoloaderGridForm(prefix=1)
        form.fields['position'].initial = 1

        grids.append(form)

        context = dict(form_general=form_general, form_params=form_params, grids=grids)
        sessions = ScreeningSession.objects.all().order_by('-date')[:10]
        context['sessions'] = sessions
        print(context['grids'])
        return context

    def post(self, request, **kwargs):
        is_viewer_only = viewer_only(self.request.user)
        form_general = ScreeningSessionForm(request.POST)
        form_params = GridCollectionParamsForm(request.POST)
        if not is_viewer_only:

            num_grids = set([k.split('-')[0] for k in request.POST.keys() if k.split('-')[0].isnumeric()])

            if form_general.is_valid() and form_params.is_valid():

                session, created = ScreeningSession.objects.get_or_create(**form_general.cleaned_data, date=datetime.today().strftime('%Y%m%d'))
                if created:
                    logger.debug(f'{session} newly created')

                else:
                    logger.debug(f'{session} exists')
                params, created = GridCollectionParams.objects.get_or_create(**form_params.cleaned_data)
                if created:
                    logger.debug(f'{params} newly created')
                else:
                    logger.debug(f'{params} exists')

                grids = []
                for i in num_grids:
                    form = AutoloaderGridForm(request.POST, prefix=i)

                    if form.is_valid():
                        if form.cleaned_data['name'] != '':
                            protocol = form.cleaned_data.pop('protocol')
                            grid, created = AutoloaderGrid.objects.get_or_create(**form.cleaned_data, session_id=session, params_id=params)
                            
                            if created:
                                logger.debug(f'{grid} newly created, creating directories')
                                create_grid_directories(grid.directory)
                            else:
                                logger.debug(f'{grid} exists')
                            logger.debug(f'Setting protocol {protocol} for {grid}')
                            get_protocol(grid,protocol)

                # session.export(export_all=False)
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
            print('PID:', pid)
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
        logger.debug(' '.join(['nohup', 'python', os.path.join(settings.BASE_DIR,
                                                        'autoscreen.py'), self.session.session_id]))
        proc = sub.Popen(['nohup', 'python', os.path.join(settings.BASE_DIR,
                                                          'autoscreen.py'), self.session.session_id], stdin=None, stdout=None, stderr=None, preexec_fn=os.setpgrp)
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
