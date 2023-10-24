from typing import Optional, Dict, Any
from django import forms
from django.urls import reverse
from Smartscope.core.models import *
from Smartscope.core.settings.worker import SMARTSCOPE_CUSTOM_CONFIG, SMARTSCOPE_DEFAULT_CONFIG, PROTOCOLS_FACTORY 
from Smartscope.core.preprocessing_pipelines import PREPROCESSING_PIPELINE_FACTORY
import yaml
from django.urls import reverse




class ScreeningSessionForm(forms.ModelForm):
    class Meta:
        from Smartscope.core.models.screening_session import ScreeningSession
        model = ScreeningSession
        fields = ("session", "group", "user", "microscope_id", "detector_id", )  # 'atlas_x', 'atlas_y', 'squares_num', 'holes_per_square', 'target_defocus'
        labels = {"session": 'Session Name',
                  "group": 'Group',
                  "user": "User",
                  "microscope_id": "Microscope",
                  "detector_id": "Detector",
                  }
        help_texts = {"session": 'Date will be automatically set. Use only [Aa-Zz], [1-9], _ and -',
                      "group": 'Field is required',
                      "user": "Optionally select a user.",
                      "microscope_id": "Field is required",
                      "detector_id": "Field is required",
                      }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['session'].widget.attrs.update({
            "pattern": "^[a-zA-Z0-9-_]+$"
        })
        self.fields['group'].widget.attrs.update({
            "hx-get": reverse('getUsersInGroup'),
            "hx-target":"#id_user",
            "hx-trigger":"change"
        })
        self.fields['user'].required = False
        self.fields['microscope_id'].widget.attrs.update({
            "hx-get": reverse('getMicroscopeDetectors'),
            "hx-target":"#id_detector_id",
            "hx-trigger":"change"
        })
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


def read_config(filename = 'default_collection_params.yaml'):
    collections_params = yaml.safe_load(Path(SMARTSCOPE_DEFAULT_CONFIG,filename).read_text())
    custom_collections_params = SMARTSCOPE_CUSTOM_CONFIG / filename
    if custom_collections_params.exists():
        collections_params.update(yaml.safe_load(custom_collections_params.read_text()))
    return collections_params

class AutoloaderGridForm(forms.ModelForm):
    protocol = forms.ChoiceField(choices=[('auto','auto')] + [(protocol,protocol) for protocol in PROTOCOLS_FACTORY.keys()])

    class Meta:
        from Smartscope.core.models.grid import AutoloaderGrid
        model = AutoloaderGrid
        fields = ('name', 'position', 'holeType', 'meshSize', 'meshMaterial')
        labels = dict(name='Name', position='Position', holeType='Hole Type', meshSize='Mesh Size', meshMaterial='Mesh Material')
        exclude = ['session_id', 'quality', 'notes', 'last_update', 'status', 'params_id', 'hole_angle', 'mesh_angle', 'start_time']
        help_texts = dict(name='Use only [Aa-Zz], [1-9], _ and -', position='number must be between 1 and 12')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['position'].widget.attrs.update({
            'class': 'form-control',
            'min': 0,
            'max': 12
        })
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control col-7'
            # visible.label = ''
            visible.field.required = False

        self.fields['name'].widget.attrs.update({'class': 'form-control',
                                                'placeholder': self.fields['name'].label, 'aria-label': "...",
                                                 "pattern": "^[a-zA-Z0-9-_]+$"})
        self.fields['name'].label = ''

        # visible.field.widget.attrs['placeholder'] = visible.field.label


class AutoloaderGridReportForm(forms.ModelForm):
    class Meta:
        from Smartscope.core.models.grid import AutoloaderGrid
        model = AutoloaderGrid
        exclude = ['session_id', 'position', 'name', 'quality', 'notes', 'last_update',
                   'status', 'params_id', 'hole_angle', 'mesh_angle', 'start_time']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_labels = ('Hole Type', 'Mesh Size', 'Mesh Material')
        for visible in self.visible_fields():

            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.required = False

class MyCheckBox(forms.CheckboxInput):
    template_name = 'general/mycheckbox.html'

class MultishotCheckBox(MyCheckBox):
    template_name = 'smartscopeSetup/multishot/multishot_form_fied.html'

    def __init__(self, attrs = None, check_test = None, grid_id=None) -> None:
        self.grid_id = grid_id if grid_id is not None else ""
        super().__init__(attrs, check_test)

    def get_context(self, name: str, value: Any, attrs: Optional[Any]) -> Dict[str, Any]:
        context = super().get_context(name, value, attrs)
        context['grid_id'] = self.grid_id
        return context

class GridCollectionParamsForm(forms.ModelForm):
    class Meta:
        from Smartscope.core.models.grid_collection_params import GridCollectionParams
        model = GridCollectionParams
        exclude = ['square_x','square_y']
        help_texts = dict(
            atlas_x='Number of tiles in X for the Atlas',
            atlas_y='Number of tiles in Y for the Atlas',
            squares_num='Number of squares to pick',
            holes_per_square='Number of holes per square, Use 0 to select all.',
            bis_max_distance='Max image-shift distance in microns. 0 to disable image-shift.',
            min_bis_group_size='Smaller group size for image-shift. Will be considered is distance is not 0',
            afis='Use astigmatism and beam-tilt compensation during beam-image shift. **Coma vs Image-shift calibration must be performed to use this option**',
            target_defocus_min='Lower defocus limit (closest to 0), must be negative',
            target_defocus_max='Higher defocus limit (highest defocus), must be negative',
            step_defocus='Step to take while cycling defocus values',
            drift_crit='Drift threshold before taking acquision in A/s. Use -1 to disable',
            tilt_angle='Tilt angle. For tilted data collection.',
            save_frames='Save the frames for high-mag acquisition or just the aligned sum if unchecked. The Session needs to be stopped and restarted for this change to take effect',
            zeroloss_delay='Delay in hours for the zero loss peak refinement procedure. Only takes effect if detector has an energy filter. Use -1 to deactivate',
            hardwaredark_delay= 'Delay in hours for the hardware dark acquisition. Use -1 to deactivate',
            offset_targeting='Enable targeting off-center to sample the ice gradient and carbon mesh particles. Use the Offset Distance setting to change behavior. Disabled in data collection mode unless offset distance is set.',
            offset_distance='Set a fixed offset value in microns. During screening, use -1 for a random offset dependent of the hole size. During data collection, only fixed values are allowed.',
            multishot_per_hole='Enable multishot per hole.'
        )

    # multishot_per_hole = forms.BooleanField(label='Multishot per hole', initial=False,help_text='Enable multishot per hole. The mutlishot menu will need to be filled.')
    multishot_per_hole_id = forms.CharField(label='Multishot per hole ID', required=False)


    def __init__(self, *args, grid_id=None, **kwargs):

        super().__init__(*args, **kwargs)
        self.fields['target_defocus_min'].widget.attrs.update({
            "max": 0,
            "step": 0.1
        })
        self.fields['target_defocus_max'].widget.attrs.update({
            "max": 0,
            "step": 0.1
        })
        self.fields['step_defocus'].widget.attrs.update({
            "min": 0,
            "step": 0.05
        })
        self.fields['bis_max_distance'].widget.attrs.update({
            "min": 0,
            "step": 0.5
        })
        self.fields['squares_num'].widget.attrs.update({
            "min": 0,
        })
        self.fields['holes_per_square'].widget.attrs.update({
            "min": 0,
        })
        self.fields['atlas_x'].widget.attrs.update({
            "min": 1,
        })
        self.fields['atlas_y'].widget.attrs.update({
            "min": 1,
        })
        self.fields['offset_distance'].widget.attrs.update({
            "min": -1,
            "step": 0.05
        })
        self.fields['multishot_per_hole'].widget = MultishotCheckBox(grid_id=grid_id)
        self.fields['afis'].widget = MyCheckBox()

        for visible in self.visible_fields():
            if isinstance(visible.field.widget, forms.CheckboxInput ):
                if not isinstance(visible.field.widget, MyCheckBox ):
                    visible.field.widget = MyCheckBox()
                visible.field.widget.attrs['class'] = 'form-check-input'
            else:    
                visible.field.widget.attrs['class'] = 'form-control'
            visible.field.required = False

        for field, data in read_config().items():
            if field not in self.fields.keys():
                continue
            self.fields[field].initial = data.pop('initial')
            self.fields[field].widget.attrs.update(data)


class PreprocessingPipelineIDForm(forms.Form):
    preprocessing_pipeline_id = forms.CharField(label='Preprocessing pipeline ID', required=False)


class AssingBisGroupsForm(forms.Form):
    directory = forms.CharField(max_length=100, empty_value='Micrographs', help_text='Relative directory from the root of the relion project')
    extension = forms.CharField(max_length=30, empty_value=None,
                                help_text='If changing the extension is needed. Default will be the movie extension. (i.e. _DW.mrc)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class SetMultiShotForm(forms.Form):
    detector_size_x= forms.IntegerField(label='Detector size X (pix)' ,initial=5760,min_value=0,required=True,help_text='Detector Size along the horizontal axis') #np.array([5760,4092])
    detector_size_y= forms.IntegerField(label='Detector size Y (pix)' ,initial=4096, min_value=0,required=True,help_text='Detector Size along the vertical axis')
    pixel_size= forms.FloatField(label='Pixel Size (A/pix)',min_value=0,required=True,help_text='Pixel size of the Record preset')
    beam_size = forms.IntegerField(label='Beam size (nm)', min_value=0, required=True, help_text='Beam diameter in nm')
    hole_size = forms.FloatField(label='Hole Size (um)', min_value=0, required=True, help_text='Grid hole size in micrometers')
    max_number_of_shots = forms.IntegerField(label='Maximum shots', min_value=2,initial=2,help_text='Maxmimum number of shots per hole to try.')
    max_efficiency = forms.FloatField(label='Mininum field of view in hole (%)',initial=85, min_value=0, max_value=100,help_text="Minimum percentage of the total field of view accross all shots to fall within the hole.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'   


class SelectProtocolForm(forms.Form):
    protocol = forms.ChoiceField(choices=[(protocol,protocol) for protocol in PROTOCOLS_FACTORY.keys()],
                                 label="Protocol",
                                 help_text='Select a different protocol. The session will need to be restarted to take effect')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['protocol'].widget.attrs.update({
            'class': 'form-control'
        })

class SelectPeprocessingPipilelineForm(forms.Form):
    pipeline = forms.ChoiceField( choices=[('', '----')]+[(key,val.verbose_name) for key,val in PREPROCESSING_PIPELINE_FACTORY.items()], label='Pipeline', help_text='Select from the available preprocessing pipelines.')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pipeline'].widget.attrs.update({
            'class': 'form-control',
        })