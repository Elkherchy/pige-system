"""
URLs pour l'API d'enregistrement
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecordingJobViewSet, check_stream

router = DefaultRouter()
router.register(r'jobs', RecordingJobViewSet, basename='recordingjob')

urlpatterns = [
    path('', include(router.urls)),
    path('check-stream/', check_stream, name='check-stream'),
]

