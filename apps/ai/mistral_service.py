"""
Service de résumé et analyse avec Mistral AI API
Documentation: https://docs.mistral.ai/api
"""
from mistralai import Mistral
from django.conf import settings
import logging
import os

logger = logging.getLogger(__name__)

# Client Mistral (initialisé une seule fois)
_mistral_client = None


def get_mistral_client():
    """
    Retourne le client Mistral (singleton)
    """
    global _mistral_client
    
    if _mistral_client is None:
        api_key = os.getenv('MISTRAL_API_KEY', '')
        if not api_key:
            logger.error("MISTRAL_API_KEY non configurée dans .env")
            raise ValueError("MISTRAL_API_KEY manquante")
        
        _mistral_client = Mistral(api_key=api_key)
        logger.info("Client Mistral initialisé")
    
    return _mistral_client


def call_mistral(prompt, model=None):
    """
    Appelle l'API Mistral pour générer du texte
    
    Args:
        prompt: Le prompt à envoyer
        model: Nom du modèle (par défaut: mistral-small-latest)
    
    Returns:
        str: La réponse générée
    """
    if model is None:
        model = getattr(settings, 'MISTRAL_MODEL', 'mistral-small-latest')
    
    try:
        client = get_mistral_client()
        
        logger.info(f"Appel API Mistral avec modèle {model}")
        
        response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content.strip()
        
        return ""
        
    except Exception as e:
        logger.error(f"Erreur lors de l'appel API Mistral: {str(e)}")
        return f"[Erreur API Mistral: {str(e)}]"


def summarize_text(text, max_sentences=5):
    """
    Génère un résumé du texte transcrit
    
    Args:
        text: Texte à résumer
        max_sentences: Nombre max de phrases dans le résumé
    
    Returns:
        str: Résumé généré
    """
    if not text or len(text.strip()) < 50:
        return "Texte trop court pour générer un résumé."
    
    prompt = f"""Tu es un assistant pour Radio Occitania. Résume ce texte en maximum {max_sentences} phrases claires et concises. Le résumé doit être utile pour un animateur radio qui veut savoir rapidement de quoi parle cet enregistrement.

Texte à résumer :
{text[:5000]}

Résumé :"""
    
    try:
        summary = call_mistral(prompt)
        return summary if summary else "Résumé non disponible"
    except Exception as e:
        logger.error(f"Erreur lors du résumé: {str(e)}")
        return f"[Erreur lors du résumé: {str(e)}]"


def analyze_blank_context(recording, start_time, end_time):
    """
    Analyse le contexte autour d'un blanc pour déterminer s'il est naturel
    
    Args:
        recording: Instance de Recording
        start_time: Début du blanc en secondes
        end_time: Fin du blanc en secondes
    
    Returns:
        dict: {
            'is_natural': bool,
            'confidence': float (0-1),
            'explanation': str
        }
    """
    # Extraire le contexte (5s avant et après)
    context_before_start = max(0, start_time - 5)
    context_after_end = end_time + 5
    
    # Obtenir la transcription du contexte
    from apps.ai.whisper_service import transcribe_segment
    
    text_before = transcribe_segment(
        recording.filepath,
        context_before_start,
        start_time
    )
    
    text_after = transcribe_segment(
        recording.filepath,
        end_time,
        context_after_end
    )
    
    blank_duration = end_time - start_time
    
    prompt = f"""Tu es un expert en analyse audio pour une radio. Un blanc de {blank_duration:.1f} secondes a été détecté.

Contexte AVANT le blanc (5 secondes) :
"{text_before}"

Contexte APRÈS le blanc (5 secondes) :
"{text_after}"

Détermine si ce blanc est NATUREL (transition musicale, pause intentionnelle) ou SUSPECT (coupure technique, problème).

Réponds UNIQUEMENT au format suivant (sans rien ajouter) :
NATURAL: [OUI ou NON]
CONFIDENCE: [0.0 à 1.0]
EXPLICATION: [Une phrase courte expliquant ton analyse]"""
    
    try:
        response = call_mistral(prompt)
        
        # Parser la réponse
        is_natural = False
        confidence = 0.5
        explanation = response
        
        lines = response.split('\n')
        for line in lines:
            if line.startswith('NATURAL:'):
                is_natural = 'OUI' in line.upper()
            elif line.startswith('CONFIDENCE:'):
                try:
                    confidence = float(line.split(':')[1].strip())
                except:
                    pass
            elif line.startswith('EXPLICATION:'):
                explanation = line.split(':', 1)[1].strip()
        
        return {
            'is_natural': is_natural,
            'confidence': confidence,
            'explanation': explanation
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du blanc: {str(e)}")
        return {
            'is_natural': False,
            'confidence': 0.0,
            'explanation': f"Erreur d'analyse: {str(e)}"
        }


def extract_keywords(text, max_keywords=10):
    """
    Extrait les mots-clés principaux d'un texte
    
    Args:
        text: Texte à analyser
        max_keywords: Nombre maximum de mots-clés
    
    Returns:
        list: Liste de mots-clés
    """
    if not text or len(text.strip()) < 20:
        return []
    
    prompt = f"""Extrait les {max_keywords} mots-clés les plus importants de ce texte. Réponds UNIQUEMENT avec les mots-clés séparés par des virgules, sans numérotation ni explication.

Texte :
{text[:2000]}

Mots-clés :"""
    
    try:
        response = call_mistral(prompt)
        keywords = [kw.strip() for kw in response.split(',')]
        return keywords[:max_keywords]
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des mots-clés: {str(e)}")
        return []


def get_model_info():
    """
    Retourne les informations sur le modèle Mistral configuré
    """
    return {
        'model': getattr(settings, 'MISTRAL_MODEL', 'mistral-small-latest'),
        'provider': 'Mistral AI API',
        'api_url': 'https://api.mistral.ai/v1/chat/completions',
        'api_key_configured': bool(os.getenv('MISTRAL_API_KEY'))
    }

