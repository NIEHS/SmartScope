"""
ASGI config for autoscreenServer project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os
from django.conf import settings
import django


django.setup()

# from channels.routing import ProtocolTypeRouter
# from django.core.asgi import get_asgi_application
from Smartscope.server.websocket.routing import application



from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application
application = ProtocolTypeRouter({
  'http': get_asgi_application(),
})
