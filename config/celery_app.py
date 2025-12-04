"""
Celery configuration for Radio Occitania Pige System
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('pige_system')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    'cleanup-expired-recordings': {
        'task': 'apps.archive.tasks.cleanup_expired_files',
        'schedule': crontab(hour=3, minute=0),  # Tous les jours à 3h
    },
    'check-storage-health': {
        'task': 'apps.recorder.tasks.check_storage_health',
        'schedule': crontab(minute='*/30'),  # Toutes les 30 minutes
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

