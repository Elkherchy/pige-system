"""
URLs pour l'API d'authentification
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('', include('rest_framework.urls')),  # Login/logout pour browsable API
]

