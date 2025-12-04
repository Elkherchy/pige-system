"""
Modèles pour le service d'enregistrement
"""
from django.db import models


class RecordingJob(models.Model):
    """
    Job d'enregistrement en cours ou programmé
    """
    STATUS_CHOICES = [
        ('scheduled', 'Programmé'),
        ('running', 'En cours'),
        ('stopped', 'Arrêté'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]
    
    source_url = models.CharField(
        max_length=1024,
        verbose_name='URL source'
    )
    output_path = models.CharField(
        max_length=2048,
        verbose_name='Chemin de sortie'
    )
    format = models.CharField(
        max_length=32,
        default='wav',
        verbose_name='Format'
    )
    quality = models.CharField(
        max_length=32,
        default='192k',
        verbose_name='Qualité'
    )
    duration = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Durée (secondes)'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name='Statut'
    )
    process_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='PID du processus'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Créé le'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Démarré le'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Terminé le'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Message d\'erreur'
    )
    
    class Meta:
        verbose_name = 'Job d\'enregistrement'
        verbose_name_plural = 'Jobs d\'enregistrement'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Job {self.id} - {self.get_status_display()}"

