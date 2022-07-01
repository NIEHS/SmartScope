
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
import os
import Smartscope

from django.contrib.auth import views as auth_views


class MyLoginView(auth_views.LoginView):
    template_name = 'login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'version': Smartscope.__version__})
        return context


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
