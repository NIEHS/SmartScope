from django.urls import path, re_path
from django.conf.urls.static import static
from django.conf import settings
from django.views.static import serve
from django.views.generic import RedirectView


from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='browse/'), name=''),
    path('browse/', views.AutoScreenViewer.as_view(), name='browser'),
    path('evaluatemicrographs/', views.EvaluateMicrographs.as_view(), name='evaluatemicrographs'),
    path('multishot/', views.MultiShotView.as_view(),name='setMultishot'),
    path('protocol/<grid_id>',views.ProtocolView.as_view(), name='protocol'),

]
if settings.USE_MICROSCOPE:
    urlpatterns += [path('run/', RedirectView.as_view(url='setup/'), name='run'),
                    path('run/setup/', views.AutoScreenSetup.as_view(), name='setup_autoscreen'),
                    path('run/session/', views.AutoScreenRun.as_view(), name='run_autoscreen'),
                    path('run/session/<session_id>/', views.AutoScreenRun.as_view(), name='run_session'),
                    ]
