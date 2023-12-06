from channels.routing import URLRouter

# from django.conf.urls import url
from django.urls import path
from .consumers import MetadataConsumer

router= URLRouter([
            path("websocket/grid_id=<grid_id>", MetadataConsumer.as_asgi())
            ])
