"""
Tâches Celery pour le recorder
"""
from celery import shared_task
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_storage_health():
    """
    Vérifie l'espace disque disponible et envoie une alerte si nécessaire
    """
    import shutil
    
    media_root = settings.MEDIA_ROOT
    
    try:
        stat = shutil.disk_usage(media_root)
        total = stat.total
        used = stat.used
        free = stat.free
        percent_used = (used / total) * 100
        
        logger.info(
            f"Espace disque: {used / (1024**3):.2f}GB utilisé / "
            f"{total / (1024**3):.2f}GB total ({percent_used:.1f}%)"
        )
        
        # Alerte si > 85% utilisé
        if percent_used > 85:
            from django.core.mail import send_mail
            
            send_mail(
                subject='[Radio Occitania] Espace disque critique',
                message=f"""
L'espace disque est critique !

Utilisé: {used / (1024**3):.2f}GB
Total: {total / (1024**3):.2f}GB
Pourcentage: {percent_used:.1f}%

Veuillez libérer de l'espace ou augmenter la capacité.
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.NOTIFY_EMAIL],
                fail_silently=True,
            )
            logger.warning(f"Alerte espace disque envoyée ({percent_used:.1f}% utilisé)")
        
        return {
            'total_gb': total / (1024**3),
            'used_gb': used / (1024**3),
            'free_gb': free / (1024**3),
            'percent_used': percent_used
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du stockage: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_failed_jobs():
    """
    Nettoie les jobs échoués ou abandonnés
    """
    from .models import RecordingJob
    from datetime import timedelta
    from django.utils import timezone
    
    # Jobs en cours depuis plus de 24h -> probablement abandonnés
    threshold = timezone.now() - timedelta(hours=24)
    stale_jobs = RecordingJob.objects.filter(
        status='running',
        started_at__lt=threshold
    )
    
    count = 0
    for job in stale_jobs:
        job.status = 'failed'
        job.error_message = 'Job abandonné (timeout)'
        job.save()
        count += 1
    
    logger.info(f"{count} job(s) abandonné(s) nettoyé(s)")
    return count

