"""
Modèles d'authentification personnalisés
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utilisateur personnalisé avec rôles pour le système de pige
    """
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('operator', 'Opérateur'),
        ('viewer', 'Observateur'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='viewer',
        verbose_name='Rôle'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Téléphone'
    )
    notifications_enabled = models.BooleanField(
        default=True,
        verbose_name='Notifications activées'
    )
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def can_manage_recordings(self):
        """Vérifie si l'utilisateur peut gérer les enregistrements"""
        return self.role in ['admin', 'operator']
    
    def can_view_analytics(self):
        """Vérifie si l'utilisateur peut voir les analyses"""
        return self.role in ['admin', 'operator', 'viewer']

