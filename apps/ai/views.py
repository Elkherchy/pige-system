"""
Vues API pour les services IA
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .whisper_service import transcribe_file, get_model_info as get_whisper_info
from .mistral_service import (
    summarize_text,
    extract_keywords,
    get_model_info as get_mistral_info
)
from apps.archive.models import Recording


@api_view(['POST'])
def transcribe(request):
    """
    Transcrit un enregistrement
    
    Body params:
    - recording_id: ID de l'enregistrement
    - language: Langue (optionnel, défaut: fr)
    """
    recording_id = request.data.get('recording_id')
    language = request.data.get('language', 'fr')
    
    if not recording_id:
        return Response(
            {'error': 'Le paramètre "recording_id" est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        recording = Recording.objects.get(pk=recording_id)
    except Recording.DoesNotExist:
        return Response(
            {'error': 'Enregistrement introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        text = transcribe_file(recording.filepath, language)
        recording.transcript = text
        recording.save()
        
        return Response({
            'success': True,
            'recording_id': recording.id,
            'transcript': text,
            'length': len(text)
        })
    except Exception as e:
        return Response(
            {'error': f'Erreur lors de la transcription: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def summarize(request):
    """
    Génère un résumé d'un enregistrement
    
    Body params:
    - recording_id: ID de l'enregistrement
    - max_sentences: Nombre max de phrases (optionnel)
    """
    recording_id = request.data.get('recording_id')
    max_sentences = request.data.get('max_sentences', 5)
    
    if not recording_id:
        return Response(
            {'error': 'Le paramètre "recording_id" est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        recording = Recording.objects.get(pk=recording_id)
    except Recording.DoesNotExist:
        return Response(
            {'error': 'Enregistrement introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier qu'il y a une transcription
    if not recording.transcript:
        return Response(
            {'error': 'Aucune transcription disponible. Lancez d\'abord la transcription.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        summary = summarize_text(recording.transcript, max_sentences)
        recording.summary = summary
        recording.save()
        
        return Response({
            'success': True,
            'recording_id': recording.id,
            'summary': summary
        })
    except Exception as e:
        return Response(
            {'error': f'Erreur lors du résumé: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def extract_keywords_view(request):
    """
    Extrait les mots-clés d'un enregistrement
    
    Body params:
    - recording_id: ID de l'enregistrement
    - max_keywords: Nombre max de mots-clés (optionnel)
    """
    recording_id = request.data.get('recording_id')
    max_keywords = request.data.get('max_keywords', 10)
    
    if not recording_id:
        return Response(
            {'error': 'Le paramètre "recording_id" est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        recording = Recording.objects.get(pk=recording_id)
    except Recording.DoesNotExist:
        return Response(
            {'error': 'Enregistrement introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if not recording.transcript:
        return Response(
            {'error': 'Aucune transcription disponible'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        keywords = extract_keywords(recording.transcript, max_keywords)
        
        # Mettre à jour les tags
        recording.tags = keywords
        recording.save()
        
        return Response({
            'success': True,
            'recording_id': recording.id,
            'keywords': keywords
        })
    except Exception as e:
        return Response(
            {'error': f'Erreur lors de l\'extraction: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def models_info(request):
    """
    Retourne les informations sur les modèles IA configurés
    """
    return Response({
        'whisper': get_whisper_info(),
        'mistral': get_mistral_info()
    })

