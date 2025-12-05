"""
URLs pour l'API d'enregistrement
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RecordingJobViewSet, 
    check_stream, 
    upload_audio,
    download_from_mongodb
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'jobs', RecordingJobViewSet, basename='recordingjob')

urlpatterns = [
    # ViewSet routes (jobs)
    path('', include(router.urls)),
    
    # Routes personnalisées conformes au frontend
    # POST /api/recordings/upload
    path('upload/', upload_audio, name='upload-audio'),
    
    # GET /api/recordings/download/mongo/<file_id>
    path('download/mongo/<str:file_id>/', download_from_mongodb, name='download-mongodb'),
    
    # POST /api/recordings/check-stream/
    path('check-stream/', check_stream, name='check-stream'),
    
    # Routes pour les jobs (via le ViewSet) :
    # POST /api/recordings/jobs/start/
    # POST /api/recordings/jobs/{jobId}/stop/
    # DELETE /api/recordings/jobs/{jobId}/
    # GET /api/recordings/jobs/active/
]

