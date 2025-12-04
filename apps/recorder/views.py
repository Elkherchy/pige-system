"""
Vues API pour le service d'enregistrement
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from datetime import datetime
import os

from .models import RecordingJob
from .services import (
    build_filename,
    start_record,
    stop_record,
    check_stream_health
)
from apps.archive.models import Recording


class RecordingJobViewSet(viewsets.ReadOnlyModelViewSet):
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
        recording = Recording.objects.create(
            title=title,
            filename=filename,
            filepath=out_path,
            format=fmt,
            bitrate=quality,
            status='recording',
            owner=request.user
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
    
    @action(detail=False, methods=['post'])
    def stop(self, request):
        """
        Arrête un enregistrement en cours
        
        Body params:
        - job_id: ID du job à arrêter
        """
        job_id = request.data.get('job_id')
        
        if not job_id:
            return Response(
                {'error': 'Le paramètre "job_id" est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            job = RecordingJob.objects.get(pk=job_id)
            
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
                
        except RecordingJob.DoesNotExist:
            return Response(
                {'error': 'Job introuvable'},
                status=status.HTTP_404_NOT_FOUND
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

