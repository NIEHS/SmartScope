from datetime import datetime
from typing import Literal
import logging
# import plotly.graph_objs as go
# import plotly.express as px
from django.http import HttpResponse, HttpRequest
from django.template.response import TemplateResponse
from django.core.cache import cache

from Smartscope.core.models import AutoloaderGrid, HoleModel, SquareModel, AtlasModel
from Smartscope.core.status import status
from Smartscope.core.svg_plots import drawBase
from Smartscope.core.settings.server_docker import AUTOSCREENDIR

logger =logging.getLogger(__name__)


def parse_maglevel(maglevel='square'):
    if maglevel == 'square':
        return SquareModel, dict()
    elif maglevel == 'atlas':
        return AtlasModel, dict()
    elif maglevel == 'hole':
        return HoleModel, dict(bis_type='center')
    
def rotate_class_color(class_color):
    if class_color == "#0000ff":
        return "#00ff00"
    if class_color == "#00ff00":
        return "#ff0000"
    if class_color == "#ff0000":
        return "#0000ff"
    
def rotate_class_number(class_number):
    return class_number + 1

def create_new_annotation_class(annotation_name):
    annotation =dict(annotation_name=annotation_name,classes=[dict(class_number=0, class_color="#0000ff")])
    cache.set(f"annotation_{annotation['annotation_name']}", annotation)   
    return annotation

def get_annotation_class(annotation_name):
    annotation = cache.get(f"annotation_{annotation_name}", None)
    return annotation
 
def add_annotation_class(request, name):
    annotation = get_annotation_class(name)
    annotation['classes'].append(dict(class_number=rotate_class_number(annotation['classes'][-1]['class_number']), class_color=rotate_class_color(annotation['classes'][-1]['class_color']))) 
    cache.set(f"annotation_{annotation['annotation_name']}", annotation)    
    return TemplateResponse(request, 'class_form.html', context=annotation['classes'][-1], status=200)

def create_new_annotation(request):
    if request.method == 'GET':
        return TemplateResponse(request, 'create_annotation.html', status=200)
    if request.method == 'POST':
        name = request.POST.get('name')
        annotation = get_annotation_class(name)
        if annotation is None:
            annotation = create_new_annotation_class(name)
        print('Returning annotation', annotation)
        return TemplateResponse(request, 'annotation_form.html', context=annotation, status=200)

def get_image(obj):
    return drawBase(obj).as_svg()

def get_images(grid_id:AutoloaderGrid, maglevel:Literal['atlas','square','hole'], num_to_plot=3):
    maglevel, extra_filters = parse_maglevel(maglevel)
    objs = maglevel.objects.filter(grid_id=grid_id, status=status.COMPLETED, **extra_filters).order_by('?')[:num_to_plot]
    plots = []
    for obj in objs:
        plots.append(get_image(obj))
    return plots

def save_annotation(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    data = request.POST
    annotation_name = data.get('annotation_name')
    annotation = get_annotation_class(annotation_name)
    cache.set(f"annotation_{annotation['annotation_name']}", annotation)    
    return TemplateResponse(request, 'annotation_form.html', context=annotation, status=200)

def annotator_view(request, grid_id, maglevel='square'):
    logger.debug(f'Grid_id = {grid_id}, maglevel = {maglevel}')
    
    context = dict()
    context['grid_id'] = grid_id
    context['images'] = get_images(grid_id, maglevel)
    return TemplateResponse(request, 'annotator_view.html', context)
