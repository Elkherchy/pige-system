"""
URLs pour l'API IA
"""
from django.urls import path
from .views import (
    transcribe,
    summarize,
    extract_keywords_view,
    models_info
)

urlpatterns = [
    path('transcribe/', transcribe, name='transcribe'),
    path('summarize/', summarize, name='summarize'),
    path('extract-keywords/', extract_keywords_view, name='extract-keywords'),
    path('models-info/', models_info, name='models-info'),
]

