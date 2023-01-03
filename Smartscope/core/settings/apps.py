from django.apps import AppConfig


# class SmartscopeConfig(AppConfig):
#     name = 'Smartscope'
#     label = 'autoscreenViewer'


class API(AppConfig):
    name = 'Smartscope.server.api'
    label = 'API'


class Frontend(AppConfig):
    name = 'Smartscope.server.frontend'
    label = 'frontend'
