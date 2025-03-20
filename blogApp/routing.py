# routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path('ws/chat/<str:username>/', consumers.ChatConsumer.as_asgi()),
]