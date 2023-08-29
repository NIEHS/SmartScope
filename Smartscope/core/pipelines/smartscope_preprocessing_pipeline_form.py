
from django import forms

class SmartScopePreprocessingPipelineForm(forms.Form):
    n_processes = forms.IntegerField(
        initial=1,
        min_value=1,
        max_value=4,
        help_text='Number of parallel processes to use for preprocessing.'
    )
    frames_directory = forms.CharField(help_text='Locations to look for the frames file other. '+ \
        'Will look in the default smartscope/movies location by default.')

    def __init__(self, *args,**kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.required = False