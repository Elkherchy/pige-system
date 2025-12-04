"""
URLs pour l'API d'archive
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecordingViewSet, BlankAlertViewSet

router = DefaultRouter()
router.register(r'recordings', RecordingViewSet, basename='recording')
router.register(r'alerts', BlankAlertViewSet, basename='blankalert')

urlpatterns = [
    path('', include(router.urls)),
]

