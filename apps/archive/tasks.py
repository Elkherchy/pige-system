"""
Tâches Celery pour l'archive
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_recording(recording_id):
    """
    Traite un enregistrement : détection de silence, transcription, résumé
    """
    from .models import Recording, BlankAlert
    from apps.recorder.services import detect_silence_ffmpeg
    from apps.ai.whisper_service import transcribe_file
    from apps.ai.mistral_service import summarize_text, analyze_blank_context
    
    try:
        recording = Recording.objects.get(pk=recording_id)
        recording.status = 'processing'
        recording.save()
        
        logger.info(f"Traitement de l'enregistrement {recording_id}")
        
        # 1. Détection de silence
        silences = detect_silence_ffmpeg(recording.filepath)
        recording.blank_analysis = {
            'silences': [
                {'start': s[0], 'end': s[1], 'duration': s[1] - s[0]}
                for s in silences
            ],
            'count': len(silences)
        }
        
        # 2. Analyser les blancs suspects
        suspicious_threshold = getattr(
            settings,
            'SUSPICIOUS_SILENCE_DURATION',
            5.0
        )
        
        for start, end in silences:
            duration = end - start
            if duration > suspicious_threshold:
                # Créer une alerte
                alert = BlankAlert.objects.create(
                    recording=recording,
                    start_time=start,
                    end_time=end,
                    duration=duration,
                    severity='warning' if duration < 10 else 'critical'
                )
                
                recording.flagged_blank = True
                
                # Analyser avec IA si transcription disponible
                # (on le fera après la transcription)
        
        recording.save()
        
        # 3. Transcription
        logger.info(f"Transcription de {recording.filename}")
        transcript = transcribe_file(recording.filepath)
        recording.transcript = transcript
        recording.save()
        
        # 4. Analyser les blancs avec contexte
        if recording.blank_alerts.exists():
            for alert in recording.blank_alerts.filter(ai_confidence__isnull=True):
                analysis = analyze_blank_context(
                    recording,
                    alert.start_time,
                    alert.end_time
                )
                alert.is_natural = analysis.get('is_natural', False)
                alert.ai_confidence = analysis.get('confidence', 0.5)
                alert.ai_explanation = analysis.get('explanation', '')
                alert.save()
                
                # Envoyer notification si suspect
                if not alert.is_natural and not alert.notified:
                    send_blank_notification(recording, alert)
                    alert.notified = True
                    alert.save()
        
        # 5. Résumé
        if transcript:
            logger.info(f"Génération du résumé pour {recording.filename}")
            summary = summarize_text(transcript)
            recording.summary = summary
        
        # 6. Extraire métadonnées audio
        from apps.recorder.services import get_audio_metadata
        metadata = get_audio_metadata(recording.filepath)
        recording.duration = metadata.get('duration')
        recording.sample_rate = metadata.get('sample_rate')
        recording.file_size = metadata.get('file_size')
        
        recording.status = 'completed'
        recording.save()
        
        logger.info(f"Traitement terminé pour {recording_id}")
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de {recording_id}: {str(e)}")
        try:
            recording = Recording.objects.get(pk=recording_id)
            recording.status = 'error'
            recording.save()
        except:
            pass


@shared_task
def cleanup_expired_files():
    """
    Nettoie les fichiers expirés
    """
    from .models import Recording
    
    now = timezone.now()
    expired = Recording.objects.filter(expires_at__lt=now)
    
    count = 0
    for recording in expired:
        try:
            if os.path.exists(recording.filepath):
                os.remove(recording.filepath)
                logger.info(f"Fichier supprimé: {recording.filepath}")
            recording.delete()
            count += 1
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de {recording.id}: {str(e)}")
    
    logger.info(f"{count} enregistrement(s) expiré(s) supprimé(s)")
    return count


def send_blank_notification(recording, alert):
    """
    Envoie une notification par email pour un blanc détecté
    """
    subject = f"[Radio Occitania] Blanc suspect détecté - {recording.title or recording.filename}"
    
    message = f"""
Un blanc suspect a été détecté dans l'enregistrement suivant :

Enregistrement : {recording.title or recording.filename}
Heure de début : {alert.start_time:.1f}s
Heure de fin : {alert.end_time:.1f}s
Durée : {alert.duration:.1f}s
Sévérité : {alert.get_severity_display()}

Analyse IA :
Confiance : {alert.ai_confidence * 100:.1f}%
{alert.ai_explanation}

Accédez à l'enregistrement : http://pige.radio-occitania.com/admin/archive/recording/{recording.id}/

---
Radio Occitania - Système de pige automatique
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.NOTIFY_EMAIL],
            fail_silently=False,
        )
        logger.info(f"Notification envoyée pour l'alerte {alert.id}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")

