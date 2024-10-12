from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/assignment_status/', consumers.AssignmentStatusConsumer.as_asgi()),
]
