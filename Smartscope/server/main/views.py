from django.shortcuts import render

from django.contrib.auth import logout, authenticate, login, REDIRECT_FIELD_NAME
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
# from django.core.urlresolvers import reverse
from django.views import generic
from django.views.generic import View, TemplateView, RedirectView
from django.shortcuts import redirect
import os
import glob
import json


class ChangeLog(LoginRequiredMixin, TemplateView):
    template_name = "log.html"
    login_url = '/login'
    redirect_field_name = 'redirect_to'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # if self.request.user.is_staff:
        file = kwargs['file']
        if file == 'changelog':
            context['title'] = 'Change Log'
        elif file == 'todo':
            context['title'] = 'To Do'

        context['log'] = self.read_changelog(file)
        return context

    def read_changelog(self, file):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'../../Info/{file}.txt'), 'r') as f:
            lines = f.readlines()
            lines = [l.strip().split('  ') for l in lines]
        return lines
