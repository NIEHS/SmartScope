from django.urls import path

from . import views

urlpatterns = [
    path('<grid_id>/<selector>/<maglevel>', views.selector_view, name='selector_view'),
    path('<grid_id>/<selector>/save/', views.save_selector_limits, name='save_selector_limits'),
    path('api/<grid_id>/<selector>/save', views.save_selector_limits_json, name='save_selector_limits_json'),
]
