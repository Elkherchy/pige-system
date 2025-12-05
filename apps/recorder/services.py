"""
Services pour l'enregistrement audio et la détection de silence
"""
import subprocess
import os
import re
from datetime import datetime
from pathlib import Path
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def build_filename(template, meta):
    """
    Construit un nom de fichier à partir d'un template
    
    Template supportés:
    - %text : titre
    - %d : jour (01-31)
    - %m : mois (01-12)
    - %Y : année (2025)
    - %H : heure (00-23)
    - %M : minute (00-59)
    - %S : seconde (00-59)
    
    Exemple: "%text_%d-%m_%Hh%M" avec title="emission" 
             -> "emission_04-12_14h30"
    """
    dt = meta.get('date', datetime.now())
    title = meta.get('title', 'untitled')
    
    # Nettoyer le titre (supprimer caractères spéciaux)
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'[-\s]+', '_', title)
    
    filename = template
    filename = filename.replace('%text', title)
    filename = filename.replace('%d', dt.strftime('%d'))
    filename = filename.replace('%m', dt.strftime('%m'))
    filename = filename.replace('%Y', dt.strftime('%Y'))
    filename = filename.replace('%H', dt.strftime('%H'))
    filename = filename.replace('%M', dt.strftime('%M'))
    filename = filename.replace('%S', dt.strftime('%S'))
    
    return filename


def start_record(stream_url, out_path, fmt='wav', quality='192k', duration=None):
    """
    Démarre un enregistrement FFmpeg
    
    Args:
        stream_url: URL du stream ou device (ex: http://stream.radio.com/live)
        out_path: Chemin du fichier de sortie
        fmt: Format audio (wav, mp3, flac)
        quality: Qualité (192k, 256k, 320k)
        duration: Durée en secondes (None = infini)
    
    Returns:
        subprocess.Popen: Le processus FFmpeg
    """
    ffmpeg_path = settings.FFMPEG_PATH
    
    # Créer le répertoire de sortie si nécessaire
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [ffmpeg_path, '-y', '-i', stream_url]
    
    if duration:
        cmd += ['-t', str(duration)]
    
    # Configuration selon le format
    if fmt == 'mp3':
        cmd += [
            '-vn',  # Pas de vidéo
            '-ar', '44100',  # Sample rate
            '-ac', '2',  # Stereo
            '-b:a', quality,  # Bitrate
            '-f', 'mp3',
            out_path
        ]
    elif fmt == 'flac':
        cmd += [
            '-vn',
            '-ar', '44100',
            '-ac', '2',
            '-compression_level', '8',
            '-f', 'flac',
            out_path
        ]
    else:  # wav par défaut
        cmd += [
            '-vn',
            '-ar', '44100',
            '-ac', '2',
            '-f', 'wav',
            out_path
        ]
    
    logger.info(f"Démarrage enregistrement: {' '.join(cmd)}")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return proc
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de l'enregistrement: {str(e)}")
        raise


def is_process_running(process_id):
    """
    Vérifie si un processus est en cours d'exécution
    
    Args:
        process_id: PID du processus
    
    Returns:
        bool: True si le processus est actif, False sinon
    """
    if not process_id:
        return False
    
    try:
        # Envoyer le signal 0 ne fait rien mais permet de vérifier l'existence
        os.kill(process_id, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Le processus existe mais on n'a pas les permissions
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du processus {process_id}: {str(e)}")
        return False


def stop_record(process_id):
    """
    Arrête un processus d'enregistrement
    
    Args:
        process_id: PID du processus
    """
    try:
        os.kill(process_id, 15)  # SIGTERM
        logger.info(f"Processus {process_id} arrêté")
        return True
    except ProcessLookupError:
        logger.warning(f"Processus {process_id} introuvable")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du processus: {str(e)}")
        return False


def detect_silence_ffmpeg(filepath, silence_thresh='-35dB', silence_duration=2.0):
    """
    Détecte les silences dans un fichier audio avec FFmpeg
    
    Args:
        filepath: Chemin du fichier audio
        silence_thresh: Seuil de silence en dB (ex: '-35dB')
        silence_duration: Durée minimale en secondes
    
    Returns:
        list: Liste de tuples (start_time, end_time)
    """
    if not os.path.exists(filepath):
        logger.error(f"Fichier introuvable: {filepath}")
        return []
    
    ffmpeg_path = settings.FFMPEG_PATH
    
    # Utiliser les paramètres de settings si disponibles
    silence_thresh = getattr(settings, 'SILENCE_DETECTION_THRESHOLD', silence_thresh)
    silence_duration = getattr(settings, 'SILENCE_DETECTION_DURATION', silence_duration)
    
    cmd = [
        ffmpeg_path,
        '-i', filepath,
        '-af', f'silencedetect=noise={silence_thresh}:d={silence_duration}',
        '-f', 'null',
        '-'
    ]
    
    logger.info(f"Détection de silence: {filepath}")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        _, stderr = proc.communicate()
        
        # Parser la sortie pour extraire les silences
        silences = []
        current_start = None
        
        for line in stderr.splitlines():
            if 'silence_start' in line:
                match = re.search(r'silence_start: ([\d.]+)', line)
                if match:
                    current_start = float(match.group(1))
            
            elif 'silence_end' in line and current_start is not None:
                match = re.search(r'silence_end: ([\d.]+)', line)
                if match:
                    end = float(match.group(1))
                    silences.append((current_start, end))
                    current_start = None
        
        logger.info(f"{len(silences)} silence(s) détecté(s)")
        return silences
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection de silence: {str(e)}")
        return []


def get_audio_metadata(filepath):
    """
    Extrait les métadonnées d'un fichier audio avec FFprobe
    
    Args:
        filepath: Chemin du fichier audio
    
    Returns:
        dict: Métadonnées (duration, sample_rate, channels, file_size, bitrate)
    """
    if not os.path.exists(filepath):
        logger.error(f"Fichier introuvable: {filepath}")
        return {}
    
    # FFprobe (généralement installé avec FFmpeg)
    ffprobe_path = settings.FFMPEG_PATH.replace('ffmpeg', 'ffprobe')
    
    cmd = [
        ffprobe_path,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        filepath
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        import json
        data = json.loads(result.stdout)
        
        format_data = data.get('format', {})
        audio_stream = next(
            (s for s in data.get('streams', []) if s.get('codec_type') == 'audio'),
            {}
        )
        
        metadata = {
            'duration': float(format_data.get('duration', 0)),
            'file_size': int(format_data.get('size', 0)),
            'bitrate': format_data.get('bit_rate', ''),
            'sample_rate': int(audio_stream.get('sample_rate', 0)),
            'channels': int(audio_stream.get('channels', 2)),
            'codec': audio_stream.get('codec_name', ''),
        }
        
        return metadata
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des métadonnées: {str(e)}")
        return {}


def check_stream_health(stream_url, timeout=5):
    """
    Vérifie la santé d'un stream audio
    
    Args:
        stream_url: URL du stream
        timeout: Timeout en secondes
    
    Returns:
        dict: {'available': bool, 'error': str}
    """
    ffmpeg_path = settings.FFMPEG_PATH
    
    cmd = [
        ffmpeg_path,
        '-t', '1',  # Tester pendant 1 seconde
        '-i', stream_url,
        '-f', 'null',
        '-'
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0 or 'time=' in result.stderr:
            return {'available': True, 'error': ''}
        else:
            return {'available': False, 'error': result.stderr}
            
    except subprocess.TimeoutExpired:
        return {'available': False, 'error': 'Timeout'}
    except Exception as e:
        return {'available': False, 'error': str(e)}

