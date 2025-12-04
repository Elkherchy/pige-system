"""
Service de transcription audio avec Whisper
Supporte à la fois l'installation locale et les API externes
"""
from django.conf import settings
import logging
import os

logger = logging.getLogger(__name__)

# Import optionnel de Whisper (si installé localement)
try:
    import whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper non installé localement, utilisation d'API externe recommandée")

# Initialisation du modèle Whisper (lazy loading)
_whisper_model = None


def get_whisper_model():
    """
    Charge le modèle Whisper (singleton) - uniquement si installé localement
    """
    global _whisper_model
    
    if not WHISPER_AVAILABLE:
        raise ImportError("Whisper n'est pas installé. Installez avec: pip install openai-whisper torch")
    
    if _whisper_model is None:
        model_name = getattr(settings, 'WHISPER_MODEL', 'base')
        device = getattr(settings, 'WHISPER_DEVICE', 'cpu')
        
        logger.info(f"Chargement du modèle Whisper '{model_name}' sur {device}")
        
        try:
            _whisper_model = whisper.load_model(
                model_name,
                device=device
            )
            logger.info("Modèle Whisper chargé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de Whisper: {str(e)}")
            raise
    
    return _whisper_model


def transcribe_file(filepath, language='fr'):
    """
    Transcrit un fichier audio en texte
    
    Args:
        filepath: Chemin du fichier audio
        language: Langue de transcription (fr, en, etc.)
    
    Returns:
        str: Texte transcrit
    """
    if not os.path.exists(filepath):
        logger.error(f"Fichier introuvable: {filepath}")
        return ""
    
    if not WHISPER_AVAILABLE:
        logger.warning("Whisper non disponible - transcription désactivée")
        return "[Transcription désactivée - Whisper non installé. Installez avec: pip install openai-whisper torch]"
    
    try:
        model = get_whisper_model()
        
        logger.info(f"Transcription de {filepath} (langue: {language})")
        
        # Options de transcription
        result = model.transcribe(
            filepath,
            language=language,
            fp16=torch.cuda.is_available() if WHISPER_AVAILABLE else False,
            verbose=False
        )
        
        text = result.get('text', '').strip()
        
        logger.info(f"Transcription terminée ({len(text)} caractères)")
        
        return text
        
    except Exception as e:
        logger.error(f"Erreur lors de la transcription: {str(e)}")
        return f"[Erreur de transcription: {str(e)}]"


def transcribe_segment(filepath, start_time, end_time, language='fr'):
    """
    Transcrit un segment spécifique d'un fichier audio
    
    Args:
        filepath: Chemin du fichier audio
        start_time: Début en secondes
        end_time: Fin en secondes
        language: Langue de transcription
    
    Returns:
        str: Texte transcrit du segment
    """
    # Note: Whisper ne supporte pas nativement les segments
    # On pourrait extraire le segment avec FFmpeg d'abord
    
    from apps.recorder.services import get_audio_metadata
    import subprocess
    import tempfile
    
    try:
        # Extraire le segment avec FFmpeg
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
        
        ffmpeg_path = settings.FFMPEG_PATH
        duration = end_time - start_time
        
        cmd = [
            ffmpeg_path,
            '-i', filepath,
            '-ss', str(start_time),
            '-t', str(duration),
            '-vn',
            '-ar', '16000',  # Whisper préfère 16kHz
            '-ac', '1',  # Mono pour Whisper
            tmp_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Transcrire le segment
        text = transcribe_file(tmp_path, language)
        
        # Nettoyer
        os.remove(tmp_path)
        
        return text
        
    except Exception as e:
        logger.error(f"Erreur lors de la transcription du segment: {str(e)}")
        return ""


def get_model_info():
    """
    Retourne les informations sur le modèle Whisper chargé
    """
    if not WHISPER_AVAILABLE:
        return {
            'available': False,
            'message': 'Whisper non installé. Installez avec: pip install openai-whisper torch'
        }
    
    model_name = getattr(settings, 'WHISPER_MODEL', 'base')
    device = getattr(settings, 'WHISPER_DEVICE', 'cpu')
    
    return {
        'available': True,
        'model': model_name,
        'device': device,
        'loaded': _whisper_model is not None
    }

