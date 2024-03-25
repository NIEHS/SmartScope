from datetime import datetime
import logging
import plotly.graph_objs as go
import plotly.express as px
from django.template.response import TemplateResponse

from Smartscope.core.models import AutoloaderGrid, HoleModel
from Smartscope.lib.Datatypes.selector_sorter import SelectorSorter
from Smartscope.core.settings.worker import PLUGINS_FACTORY

logger =logging.getLogger(__name__)


def initialize_selector(grid_id, selector:str) -> SelectorSorter:
    selector_sorter = SelectorSorter(selector=PLUGINS_FACTORY[selector],targets=HoleModel.display.filter(grid_id=grid_id, square_id='grid1_square11BeZGKcjKyUKT3nQh'))
    return selector_sorter

def set_transparent_background(fig):
    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        })
    return fig

def plot_bars_selector(selector_sorter:SelectorSorter):
    data = list(selector_sorter.values)
    fig = px.histogram(x=data, nbins=int(abs(min(data) - max(data))), labels={'x': 'Values', 'color': 'Clusters'})
    # layout = go.Layout(title='Selector distribution', xaxis=dict(title='Labels'), yaxis=dict(title='Values'), showlegend=False)
    # fig = go.Figure(data=[trace], layout=layout)
    fig.add_vline(x=selector_sorter.limits[0], line_width=3, line_color="black")
    fig.add_vline(x=selector_sorter.limits[1], line_width=3, line_color="black")
    fig = set_transparent_background(fig)
    return fig.to_html(full_html=False, config = {'displayModeBar': False})

def plot_scatter_selector(selector_sorter:SelectorSorter):
    data = list(selector_sorter.values)
    fig = px.scatter(y=data, labels={'x': 'Holes','y': 'Selector Value', 'color': 'Clusters'})
    fig.add_hrect(y0=selector_sorter.limits[0], y1=selector_sorter.limits[1], fillcolor='lightgreen', opacity=0.5, line_width=0)
    fig = set_transparent_background(fig)
    return fig.to_html(full_html=False, config = {'displayModeBar': False}, div_id='selector_plot')

def selector_view(request, grid_id, selector):
    logger.debug(f'Grid_id = {grid_id}, selector = {selector}')
    context = dict()
    context['grid_id'] = grid_id
    selector_sorter = initialize_selector(grid_id, selector)
    context['selector'] = selector_sorter._selector
    
    context['graph'] = plot_scatter_selector(selector_sorter)
    return TemplateResponse(request, 'selector_view.html', context)





# class CollectionStatsView(TemplateView):
#     template_name = "autoscreenViewer/collection_stats.html"

#     def ctfGraph(self,grid_id):
#         ### NEED TO MOVE THE GRAPHING LOGIC OUTSIDE OF HERE
#         all_data = list(HighMagModel.objects.filter(status='completed', grid_id=grid_id).order_by('completion_time').values_list('ctffit', flat=True)) # replace with your own data source
#         all_data = list(map(lambda x: 15 if x > 15 else x, all_data))
#         latest_data = all_data[-100:]
#         hist_all = go.Histogram(x=all_data, nbinsx=30, name='All')
#         hist_latest = go.Histogram(x=latest_data, nbinsx=30, name='Latest 100')


#         layout = go.Layout(
#                             title='CTF fit distribution',
#                             xaxis=dict(
#                                 title='CTF fit resolution (Angstrom)',
#                             ),
#                             yaxis=dict(
#                                 title='Number of exposures'
#                             ),
#                             showlegend=True,
#                         )
#         fig = go.Figure(data=[hist_all,hist_latest],layout=layout,)

        
#         graph = fig.to_html(full_html=False)
#         return graph
    
#     def ice_thickness_graph(self,grid_id):
#         ### NEED TO MOVE THE GRAPHING LOGIC OUTSIDE OF HERE
#         all_data = list(HighMagModel.objects.filter(status='completed', grid_id=grid_id, ice_thickness__isnull=False).order_by('completion_time').values_list('ice_thickness', flat=True)) # replace with your own data source
#         # all_data = list(map(lambda x: 15 if x > 15 else x, all_data))
#         latest_data = all_data[-100:]
#         hist_all = go.Histogram(x=all_data, nbinsx=30, name='All')
#         hist_latest = go.Histogram(x=latest_data, nbinsx=30, name='Latest 100')


#         layout = go.Layout(
#                             title='Ice thickness distribution',
#                             xaxis=dict(
#                                 title='Esstimated ice thickness (nm)',
#                             ),
#                             yaxis=dict(
#                                 title='Number of exposures'
#                             ),
#                             showlegend=True,
#                         )
#         fig = go.Figure(data=[hist_all,hist_latest],layout=layout,)

        
#         graph = fig.to_html(full_html=False)
#         return graph

#     def get_context_data(self, grid_id, **kwargs):
#         context = super().get_context_data(**kwargs)
#         grid= AutoloaderGrid.objects.get(pk=grid_id)
#         context.update(get_hole_count(grid))
#         context['graph'] = self.ctfGraph(grid_id)
#         context['ice_thickness_graph'] = self.ice_thickness_graph(grid_id)
#         return context
    
#     def get(self,request, grid_id, *args, **kwargs):
#         context = self.get_context_data(grid_id, **kwargs)
#         return render(request,self.template_name, context)
    
# def getUsersInGroup(request):
#     group = request.GET.get('group',None)
#     if group is None:
#         return HttpResponse('Group not specified')
#     users = User.objects.filter(groups__name=group)
#     options = [{"value":u.username,"field":u.username} for u in users] 

#     return render(request, "general/options_fields.html", {"options": options})

# def getMicroscopeDetectors(request):
#     microscope = request.GET.get('microscope_id',None)
#     if microscope is None:
#         return HttpResponse('Microscope not specified')
#     detectors = Detector.objects.filter(microscope_id=microscope)
#     options = [{"value":d.pk,"field":d} for d in detectors]
#     return render(request, "general/options_fields.html", {"options": options})