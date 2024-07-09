from django.conf import settings  # import the settings file
from pathlib import Path

def get_version():
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {'VERSION': Path('VERSION').read_text()}

def base_settings(request):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {'USE_MICROSCOPE': settings.USE_MICROSCOPE,} | get_version()
