"""
Modèles pour l'archivage des enregistrements
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

User = get_user_model()


class Recording(models.Model):
    """
    Enregistrement audio avec métadonnées et analyses
    """
    STATUS_CHOICES = [
        ('recording', 'En cours'),
        ('processing', 'Traitement'),
        ('completed', 'Terminé'),
        ('error', 'Erreur'),
    ]
    
    # Identification
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Titre'
    )
    filename = models.CharField(
        max_length=1024,
        verbose_name='Nom du fichier'
    )
    filepath = models.CharField(
        max_length=2048,
        verbose_name='Chemin du fichier'
    )
    
    # MongoDB Storage
    mongo_file_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='ID fichier MongoDB',
        help_text='ID du fichier dans MongoDB GridFS'
    )
    mongo_url = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name='URL MongoDB',
        help_text='URL pour télécharger depuis MongoDB'
    )
    local_url = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name='URL locale',
        help_text='URL pour télécharger depuis le stockage local'
    )
    
    # Métadonnées audio
    duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Durée (secondes)'
    )
    format = models.CharField(
        max_length=32,
        default='wav',
        verbose_name='Format'
    )
    bitrate = models.CharField(
        max_length=32,
        blank=True,
        verbose_name='Débit'
    )
    sample_rate = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Taux d\'échantillonnage'
    )
    channels = models.IntegerField(
        default=2,
        verbose_name='Canaux'
    )
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='Taille du fichier (octets)'
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='recording',
        verbose_name='Statut'
    )
    
    # Détection de silence
    flagged_blank = models.BooleanField(
        default=False,
        verbose_name='Blanc détecté'
    )
    blank_analysis = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Analyse des blancs'
    )
    
    # Analyses IA
    transcript = models.TextField(
        blank=True,
        verbose_name='Transcription'
    )
    summary = models.TextField(
        blank=True,
        verbose_name='Résumé'
    )
    ai_metadata = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Métadonnées IA'
    )
    
    # Gestion
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recordings',
        verbose_name='Propriétaire'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Date de modification'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date d\'expiration'
    )
    
    # Tags et recherche
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Tags'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    
    class Meta:
        verbose_name = 'Enregistrement'
        verbose_name_plural = 'Enregistrements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['flagged_blank']),
        ]
    
    def __str__(self):
        return f"{self.title or self.filename} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Définir la date d'expiration si non définie
        if not self.expires_at and self.created_at:
            retention_days = getattr(
                settings,
                'RECORDING_DEFAULT_RETENTION_DAYS',
                30
            )
            self.expires_at = self.created_at + timedelta(days=retention_days)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Vérifie si l'enregistrement est expiré"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def duration_formatted(self):
        """Retourne la durée formatée"""
        if not self.duration:
            return "N/A"
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        if hours > 0:
            return f"{hours}h{minutes:02d}m{seconds:02d}s"
        return f"{minutes}m{seconds:02d}s"


class BlankAlert(models.Model):
    """
    Alertes pour les blancs détectés
    """
    SEVERITY_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('critical', 'Critique'),
    ]
    
    recording = models.ForeignKey(
        Recording,
        on_delete=models.CASCADE,
        related_name='blank_alerts',
        verbose_name='Enregistrement'
    )
    start_time = models.FloatField(
        verbose_name='Début (secondes)'
    )
    end_time = models.FloatField(
        verbose_name='Fin (secondes)'
    )
    duration = models.FloatField(
        verbose_name='Durée (secondes)'
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='info',
        verbose_name='Sévérité'
    )
    is_natural = models.BooleanField(
        default=False,
        verbose_name='Blanc naturel'
    )
    ai_confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Confiance IA'
    )
    ai_explanation = models.TextField(
        blank=True,
        verbose_name='Explication IA'
    )
    notified = models.BooleanField(
        default=False,
        verbose_name='Notification envoyée'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de détection'
    )
    
    class Meta:
        verbose_name = 'Alerte de blanc'
        verbose_name_plural = 'Alertes de blancs'
        ordering = ['-created_at']
    
    def __str__(self):
        return (
            f"Blanc {self.get_severity_display()} dans {self.recording} "
            f"({self.start_time:.1f}s - {self.end_time:.1f}s)"
        )
    
    @property
    def duration_formatted(self):
        """Retourne la durée formatée"""
        return f"{self.duration:.2f}s"

