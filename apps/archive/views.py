"""
Vues API pour l'archive
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse
from django.shortcuts import get_object_or_404
import os

from .models import Recording, BlankAlert
from .serializers import (
    RecordingSerializer,
    RecordingListSerializer,
    RecordingCreateSerializer,
    BlankAlertSerializer
)


class RecordingViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des enregistrements
    """
    queryset = Recording.objects.all().select_related('owner').prefetch_related('blank_alerts')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'format', 'flagged_blank', 'owner']
    search_fields = ['title', 'filename', 'transcript', 'summary', 'notes']
    ordering_fields = ['created_at', 'duration', 'title']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RecordingListSerializer
        elif self.action == 'create':
            return RecordingCreateSerializer
        return RecordingSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Télécharge le fichier audio"""
        recording = self.get_object()
        if not os.path.exists(recording.filepath):
            return Response(
                {'error': 'Fichier non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        return FileResponse(
            open(recording.filepath, 'rb'),
            as_attachment=True,
            filename=recording.filename
        )
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Déclenche le traitement manuel d'un enregistrement"""
        from apps.archive.tasks import process_recording
        recording = self.get_object()
        recording.status = 'processing'
        recording.save()
        process_recording.delay(recording.id)
        return Response({'status': 'Traitement lancé'})
    
    @action(detail=True, methods=['post'])
    def extend_retention(self, request, pk=None):
        """Prolonge la durée de rétention"""
        from datetime import timedelta
        recording = self.get_object()
        days = request.data.get('days', 30)
        if recording.expires_at:
            recording.expires_at += timedelta(days=days)
        recording.save()
        return Response({
            'status': 'Rétention prolongée',
            'expires_at': recording.expires_at
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Retourne des statistiques sur les enregistrements"""
        from django.db.models import Count, Sum, Avg
        
        stats = {
            'total_recordings': Recording.objects.count(),
            'by_status': dict(
                Recording.objects.values('status').annotate(count=Count('id'))
                .values_list('status', 'count')
            ),
            'flagged_blanks': Recording.objects.filter(flagged_blank=True).count(),
            'total_duration': Recording.objects.aggregate(
                total=Sum('duration')
            )['total'] or 0,
            'avg_duration': Recording.objects.aggregate(
                avg=Avg('duration')
            )['avg'] or 0,
            'total_size': Recording.objects.aggregate(
                total=Sum('file_size')
            )['total'] or 0,
        }
        return Response(stats)


class BlankAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour consulter les alertes de blanc
    """
    queryset = BlankAlert.objects.all().select_related('recording')
    serializer_class = BlankAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['recording', 'severity', 'is_natural', 'notified']
    ordering_fields = ['created_at', 'duration', 'severity']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def mark_as_natural(self, request, pk=None):
        """Marque un blanc comme naturel"""
        alert = self.get_object()
        alert.is_natural = True
        alert.save()
        return Response({'status': 'Marqué comme naturel'})

