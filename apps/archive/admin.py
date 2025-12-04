"""
Configuration admin pour l'archive
"""
from django.contrib import admin
from .models import Recording, BlankAlert


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'filename', 'status', 'duration_formatted',
        'flagged_blank', 'created_at', 'expires_at', 'owner'
    ]
    list_filter = ['status', 'format', 'flagged_blank', 'created_at']
    search_fields = ['title', 'filename', 'transcript', 'summary']
    readonly_fields = [
        'created_at', 'updated_at', 'duration_formatted',
        'is_expired', 'file_size'
    ]
    fieldsets = (
        ('Informations générales', {
            'fields': ('title', 'filename', 'filepath', 'status', 'owner')
        }),
        ('Métadonnées audio', {
            'fields': (
                'duration', 'duration_formatted', 'format', 'bitrate',
                'sample_rate', 'channels', 'file_size'
            )
        }),
        ('Détection de silence', {
            'fields': ('flagged_blank', 'blank_analysis')
        }),
        ('Analyses IA', {
            'fields': ('transcript', 'summary', 'ai_metadata')
        }),
        ('Gestion', {
            'fields': (
                'created_at', 'updated_at', 'expires_at',
                'is_expired', 'tags', 'notes'
            )
        }),
    )
    
    actions = ['mark_as_completed', 'extend_retention']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} enregistrement(s) marqué(s) comme terminé(s).')
    mark_as_completed.short_description = "Marquer comme terminé"
    
    def extend_retention(self, request, queryset):
        from datetime import timedelta
        from django.utils import timezone
        count = 0
        for recording in queryset:
            if recording.expires_at:
                recording.expires_at += timedelta(days=30)
                recording.save()
                count += 1
        self.message_user(request, f'Rétention prolongée de 30 jours pour {count} enregistrement(s).')
    extend_retention.short_description = "Prolonger la rétention de 30 jours"


@admin.register(BlankAlert)
class BlankAlertAdmin(admin.ModelAdmin):
    list_display = [
        'recording', 'severity', 'duration_formatted',
        'is_natural', 'notified', 'created_at'
    ]
    list_filter = ['severity', 'is_natural', 'notified', 'created_at']
    search_fields = ['recording__title', 'recording__filename', 'ai_explanation']
    readonly_fields = ['created_at', 'duration_formatted']
    
    fieldsets = (
        ('Enregistrement', {
            'fields': ('recording',)
        }),
        ('Détection', {
            'fields': (
                'start_time', 'end_time', 'duration',
                'duration_formatted', 'severity'
            )
        }),
        ('Analyse IA', {
            'fields': ('is_natural', 'ai_confidence', 'ai_explanation')
        }),
        ('Notification', {
            'fields': ('notified', 'created_at')
        }),
    )

