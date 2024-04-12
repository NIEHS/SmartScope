from django.urls import path, re_path
from django.conf.urls.static import static
from django.conf import settings
from django.views.static import serve
from django.views.generic import RedirectView


from . import views

urlpatterns = [
    path('<grid_id>/<selector>', views.selector_view, name='selector_view'),
    path('<grid_id>/<selector>/save/', views.save_selector_limits, name='save_selector_limits'),
]
