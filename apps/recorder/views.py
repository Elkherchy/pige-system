"""
Vues API pour le service d'enregistrement
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.http import HttpResponse
from datetime import datetime
import os
import logging

from .models import RecordingJob
from .services import (
    build_filename,
    start_record,
    stop_record,
    check_stream_health
)
from apps.archive.models import Recording
from apps.archive.mongodb_service import get_mongodb_service

logger = logging.getLogger(__name__)


class RecordingJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour consulter les jobs d'enregistrement
    """
    queryset = RecordingJob.objects.all()
    permission_classes = []  # Pas d'authentification requise
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        Démarre un nouvel enregistrement
        
        Body params:
        - source: URL du stream ou device
        - title: Titre de l'enregistrement (optionnel)
        - format: Format audio (wav, mp3, flac)
        - quality: Qualité (192k, 256k, 320k)
        - duration: Durée en secondes (optionnel)
        - template: Template de nom de fichier (optionnel)
        - storage_path: Chemin de stockage personnalisé (optionnel)
        """
        data = request.data
        
        # Validation
        source = data.get('source')
        if not source:
            return Response(
                {'error': 'Le paramètre "source" est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier la santé du stream
        health = check_stream_health(source)
        if not health['available']:
            return Response(
                {'error': f'Stream indisponible: {health["error"]}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Paramètres
        title = data.get('title', '')
        fmt = data.get('format', settings.RECORDING_DEFAULT_FORMAT)
        quality = data.get('quality', settings.RECORDING_DEFAULT_QUALITY)
        duration = data.get('duration')
        template = data.get('template', '%text_%d-%m_%Hh%M')
        storage_path = data.get('storage_path', str(settings.MEDIA_ROOT))
        
        # Construire le nom de fichier
        filename = build_filename(template, {
            'title': title or 'recording',
            'date': datetime.now()
        })
        filename = f"{filename}.{fmt}"
        
        # Chemin complet
        out_path = os.path.join(storage_path, filename)
        
        # Créer le Recording dans la DB
        # Owner = None si pas authentifié, sinon request.user
        owner = request.user if request.user.is_authenticated else None
        recording = Recording.objects.create(
            title=title,
            filename=filename,
            filepath=out_path,
            format=fmt,
            bitrate=quality,
            status='recording',
            owner=owner
        )
        
        # Créer le job
        job = RecordingJob.objects.create(
            source_url=source,
            output_path=out_path,
            format=fmt,
            quality=quality,
            duration=duration,
            status='scheduled'
        )
        
        try:
            # Démarrer l'enregistrement
            proc = start_record(source, out_path, fmt, quality, duration)
            
            job.process_id = proc.pid
            job.status = 'running'
            job.save()
            
            # Programmer le traitement automatique si durée définie
            if duration:
                from apps.archive.tasks import process_recording
                process_recording.apply_async(
                    args=[recording.id],
                    countdown=duration + 10  # Attendre la fin + 10s
                )
            
            return Response({
                'success': True,
                'job_id': job.id,
                'recording_id': recording.id,
                'process_id': proc.pid,
                'output_path': out_path,
                'message': 'Enregistrement démarré'
            })
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            
            recording.status = 'error'
            recording.save()
            
            return Response(
                {'error': f'Erreur lors du démarrage: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """
        Arrête un enregistrement en cours
        
        URL: POST /api/recordings/jobs/{jobId}/stop/
        """
        try:
            job = self.get_object()
            
            if job.status != 'running':
                return Response(
                    {'error': 'Le job n\'est pas en cours d\'exécution'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not job.process_id:
                return Response(
                    {'error': 'PID du processus introuvable'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Arrêter le processus
            success = stop_record(job.process_id)
            
            if success:
                job.status = 'stopped'
                job.completed_at = datetime.now()
                job.save()
                
                # Marquer le recording comme terminé et lancer le traitement
                try:
                    recording = Recording.objects.get(filepath=job.output_path)
                    recording.status = 'processing'
                    recording.save()
                    
                    from apps.archive.tasks import process_recording
                    process_recording.delay(recording.id)
                except Recording.DoesNotExist:
                    pass
                
                return Response({
                    'success': True,
                    'message': 'Enregistrement arrêté',
                    'job_id': job.id
                })
            else:
                return Response(
                    {'error': 'Impossible d\'arrêter le processus'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Liste les enregistrements actifs"""
        active_jobs = RecordingJob.objects.filter(status='running')
        return Response({
            'count': active_jobs.count(),
            'jobs': [
                {
                    'id': job.id,
                    'source': job.source_url,
                    'output': job.output_path,
                    'format': job.format,
                    'started_at': job.started_at,
                    'process_id': job.process_id
                }
                for job in active_jobs
            ]
        })


@api_view(['POST'])
def check_stream(request):
    """
    Vérifie la disponibilité d'un stream
    
    Body params:
    - url: URL du stream à tester
    """
    url = request.data.get('url')
    
    if not url:
        return Response(
            {'error': 'Le paramètre "url" est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    health = check_stream_health(url)
    
    return Response({
        'url': url,
        'available': health['available'],
        'error': health['error'] if not health['available'] else None
    })


@api_view(['POST'])
def upload_audio(request):
    """
    Upload un fichier audio et le stocke dans MongoDB
    
    Body params (multipart/form-data):
    - audio_file: Fichier audio à uploader
    - title: Titre de l'enregistrement
    - format: Format audio (optionnel, détecté automatiquement)
    - duration: Durée en secondes (optionnel)
    """
    try:
        # Vérifier que le fichier est présent
        if 'audio_file' not in request.FILES:
            return Response(
                {'error': 'Le fichier audio_file est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        audio_file = request.FILES['audio_file']
        title = request.data.get('title', audio_file.name)
        fmt = request.data.get('format', '')
        duration = request.data.get('duration')
        
        # Détecter le format depuis l'extension si non fourni
        if not fmt:
            _, ext = os.path.splitext(audio_file.name)
            fmt = ext.lstrip('.') or 'unknown'
        
        # Créer un chemin temporaire pour le fichier
        temp_filename = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{audio_file.name}"
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', temp_filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        # Sauvegarder temporairement le fichier
        with open(temp_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)
        
        # Obtenir la taille du fichier
        file_size = os.path.getsize(temp_path)
        
        # Créer l'enregistrement dans la DB
        owner = request.user if request.user.is_authenticated else None
        recording = Recording.objects.create(
            title=title,
            filename=audio_file.name,
            filepath=temp_path,
            format=fmt,
            status='processing',
            file_size=file_size,
            owner=owner
        )
        
        # Upload vers MongoDB
        mongo_service = get_mongodb_service()
        
        # Préparer les métadonnées
        metadata = {
            'title': title,
            'format': fmt,
            'recording_id': recording.id,
            'uploaded_by': owner.username if owner else 'anonymous',
        }
        
        if duration:
            try:
                metadata['duration'] = float(duration)
                recording.duration = float(duration)
            except (ValueError, TypeError):
                pass
        
        # Upload le fichier vers MongoDB
        mongo_result = mongo_service.upload_file(
            file_path=temp_path,
            filename=audio_file.name,
            metadata=metadata
        )
        
        # Mettre à jour l'enregistrement avec les infos MongoDB
        recording.mongo_file_id = mongo_result['file_id']
        recording.mongo_url = mongo_result['url']
        recording.local_url = f"/api/recordings/{recording.id}/download/"
        recording.save()
        
        # Nettoyer le fichier temporaire (optionnel, on peut le garder comme backup)
        # os.remove(temp_path)
        
        # Programmer le traitement automatique
        from apps.archive.tasks import process_recording
        process_recording.delay(recording.id)
        
        logger.info(f"✓ Fichier uploadé avec succès: {audio_file.name} (Recording ID: {recording.id})")
        
        # Réponse conforme au format attendu par le frontend
        return Response({
            'success': True,
            'recording_id': recording.id,
            'mongo_file_id': mongo_result['file_id'],
            'mongo_url': mongo_result['url'],
            'local_url': recording.local_url,
            'filename': audio_file.name,
            'message': 'Fichier uploadé avec succès',
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"✗ Erreur lors de l'upload: {str(e)}")
        
        # Nettoyer en cas d'erreur
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        
        return Response(
            {'error': f'Erreur lors de l\'upload: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def download_from_mongodb(request, file_id):
    """
    Télécharge un fichier depuis MongoDB GridFS
    
    URL params:
    - file_id: ID du fichier dans MongoDB
    """
    try:
        mongo_service = get_mongodb_service()
        
        # Vérifier que le fichier existe
        if not mongo_service.file_exists(file_id):
            return Response(
                {'error': 'Fichier introuvable dans MongoDB'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Récupérer les métadonnées
        metadata = mongo_service.get_file_metadata(file_id)
        
        # Télécharger le fichier
        file_data = mongo_service.download_file(file_id)
        
        # Créer la réponse HTTP
        response = HttpResponse(file_data, content_type=metadata.get('content_type', 'application/octet-stream'))
        response['Content-Disposition'] = f'attachment; filename="{metadata.get("filename", "audio.mp3")}"'
        response['Content-Length'] = len(file_data)
        
        return response
        
    except Exception as e:
        logger.error(f"✗ Erreur lors du téléchargement depuis MongoDB: {str(e)}")
        return Response(
            {'error': f'Erreur lors du téléchargement: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

