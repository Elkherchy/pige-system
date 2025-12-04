"""
Configuration admin pour le recorder
"""
from django.contrib import admin
from .models import RecordingJob


@admin.register(RecordingJob)
class RecordingJobAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'status', 'format', 'source_url',
        'created_at', 'started_at', 'process_id'
    ]
    list_filter = ['status', 'format', 'created_at']
    search_fields = ['source_url', 'output_path']
    readonly_fields = [
        'created_at', 'started_at', 'completed_at', 'process_id'
    ]
    
    fieldsets = (
        ('Configuration', {
            'fields': ('source_url', 'output_path', 'format', 'quality', 'duration')
        }),
        ('Statut', {
            'fields': ('status', 'process_id', 'error_message')
        }),
        ('Dates', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
    )

