from django.conf import settings  # import the settings file


def base_settings(request):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {'USE_MICROSCOPE': settings.USE_MICROSCOPE}
