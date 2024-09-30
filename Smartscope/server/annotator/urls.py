from django.urls import path
from django.views.generic import RedirectView


from . import views

urlpatterns = [
    path('add_annotation_class/<name>', views.add_annotation_class, name='add_annotation_class'),
    path('<grid_id>/<maglevel>', views.annotator_view, name='annotator_view'),
    path('create_annotation/', views.create_new_annotation, name='create_annotation'),

    # path('<grid_id>/targetlabelr>/save/', views.save_selector_limits, name='annotator_save'),
]
