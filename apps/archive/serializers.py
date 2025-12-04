"""
Serializers pour l'API d'archive
"""
from rest_framework import serializers
from .models import Recording, BlankAlert


class BlankAlertSerializer(serializers.ModelSerializer):
    """Serializer pour les alertes de blanc"""
    duration_formatted = serializers.ReadOnlyField()
    
    class Meta:
        model = BlankAlert
        fields = [
            'id', 'recording', 'start_time', 'end_time', 'duration',
            'duration_formatted', 'severity', 'is_natural', 'ai_confidence',
            'ai_explanation', 'notified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RecordingSerializer(serializers.ModelSerializer):
    """Serializer pour les enregistrements"""
    duration_formatted = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    blank_alerts = BlankAlertSerializer(many=True, read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = Recording
        fields = [
            'id', 'title', 'filename', 'filepath', 'duration',
            'duration_formatted', 'format', 'bitrate', 'sample_rate',
            'channels', 'file_size', 'status', 'flagged_blank',
            'blank_analysis', 'transcript', 'summary', 'ai_metadata',
            'owner', 'owner_username', 'created_at', 'updated_at',
            'expires_at', 'is_expired', 'tags', 'notes', 'blank_alerts'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'duration',
            'file_size', 'is_expired'
        ]


class RecordingListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des enregistrements"""
    duration_formatted = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    blank_alerts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Recording
        fields = [
            'id', 'title', 'filename', 'duration', 'duration_formatted',
            'format', 'status', 'flagged_blank', 'blank_alerts_count',
            'owner_username', 'created_at', 'expires_at', 'is_expired'
        ]
    
    def get_blank_alerts_count(self, obj):
        return obj.blank_alerts.count()


class RecordingCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création d'enregistrements"""
    
    class Meta:
        model = Recording
        fields = [
            'title', 'filename', 'filepath', 'format', 'bitrate',
            'sample_rate', 'channels', 'owner', 'tags', 'notes'
        ]

