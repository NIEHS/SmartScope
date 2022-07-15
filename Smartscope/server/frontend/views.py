from django.shortcuts import render

from django.contrib.auth import logout, authenticate, login, REDIRECT_FIELD_NAME
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
from django.views import generic
from django.views.generic import View, TemplateView, RedirectView
from django.shortcuts import redirect
from django.db import transaction
import os
import glob
import json
from .forms import *
import subprocess as sub
import psutil
import signal
from django.utils.timezone import now
from Smartscope.core.db_manipulations import viewer_only
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print('User Staff?:', self.request.user.is_staff)
        if self.request.user.is_staff:
            context['dirs'] = sorted(list(Group.objects.all().values_list('name', flat=True)))
        else:
            context['dirs'] = sorted(list(self.request.user.groups.values_list('name', flat=True)))
        return context

    def listsubdir(self, dir, reverse=False):
        ld = sorted(os.listdir(os.path.join(settings.AUTOSCREENING, dir)), reverse=reverse)
        return [l for l in ld if l[0] != '.']

    def open_settings(self, path):
        with open(path, 'r') as f:
            adict = json.load(f)
        return adict


class GroupSessions(AutoScreenViewer):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sessions'] = ScreeningSession.objects.all().filter(group=kwargs['dir']).order_by('-date')
        return context


class GridsSession(GroupSessions):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = kwargs['session'].split('_')
        context['selected_session'] = ScreeningSession.objects.get(session='_'.join(session[1:]), date=session[0])
        context['autoloader'] = AutoloaderGrid.objects.all().filter(session_id=context['selected_session'].session_id).order_by('position')
        context['form_general'] = ScreeningSessionForm(instance=context['selected_session'])
        # print(context)
        return context


class Report(GridsSession):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['grid'] = context['selected_session'].autoloadergrid_set.get(name=kwargs['name'], position=kwargs['pos'])

        context['gridform'] = AutoloaderGridReportForm(instance=context['grid'])
        context['gridCollectionParamsForm'] = GridCollectionParamsForm(instance=context['grid'].params_id)
        context['directory'] = context['grid'].url
        context['quality_choices'] = HoleModel.QUALITY_CHOICES
        context['class_choices'] = HoleModel.CLASS_CHOICES
        try:
            context['atlas_id'] = context['grid'].atlasmodel_set.all().first().atlas_id
        except:
            context['atlas_id'] = None
        # self.directory = context['grid'].directory

        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)


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
        # for i in range(1, 13, 1):
        form = AutoloaderGridForm(prefix=1)
        form.fields['position'].initial = 1
        # form.fields['position'].widget.attrs['readonly'] = True
        # form.fields['position'].widget.attrs['class'] = "form-control-plaintext"
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
                    print(f'{session} newly created')
                else:
                    print(f'{session} exists')
                params, created = GridCollectionParams.objects.get_or_create(**form_params.cleaned_data)
                if created:
                    print(f'{params} newly created')
                else:
                    print(f'{params} exists')

                grids = []
                for i in num_grids:
                    form = AutoloaderGridForm(request.POST, prefix=i)

                    if form.is_valid():
                        if form.cleaned_data['name'] != '':
                            grid, created = AutoloaderGrid.objects.get_or_create(**form.cleaned_data, session_id=session, params_id=params)

                            if created:
                                print(f'{grid} newly created')
                            else:
                                print(f'{grid} exists')
                        # if grid.name == '':
                        #     continue
                        # else:
                        #     grid.session_id = session
                        #     grid.params_id = params
                        #     grids.append(grid)

                # with transaction.atomic():
                #     session.save()
                #     params.save()
                #     for grid in grids:
                #         grid.save()

                session.export(export_all=False)
                return redirect(f'../session/{session.session_id}')

                # print(form_general.errors)
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
            print('starting process')
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
            print('Stop process')
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
                print('GOT REQUEST!')
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
        print(' '.join(['nohup', 'python', os.path.join(settings.BASE_DIR,
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
        print('Is_running: ', is_running)
        print('status: ', proc.status())
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
