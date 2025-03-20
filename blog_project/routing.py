from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from blogApp.routing import websocket_urlpatterns  # Import from app-level

application = ProtocolTypeRouter({
    'websocket': URLRouter(websocket_urlpatterns),
})