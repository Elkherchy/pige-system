#!/bin/bash
# Script pour démarrer un enregistrement manuel avec FFmpeg

# Usage: ./start_recorder.sh <source_url> <output_file>

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <source_url> <output_file> [duration_seconds]"
    echo "Exemple: $0 http://stream.radio.com/live recording.wav 3600"
    exit 1
fi

SOURCE=$1
OUTPUT=$2
DURATION=${3:-""}

echo "======================================"
echo "Radio Occitania - Enregistrement Manuel"
echo "======================================"
echo "Source: $SOURCE"
echo "Sortie: $OUTPUT"
if [ -n "$DURATION" ]; then
    echo "Durée: $DURATION secondes"
else
    echo "Durée: Infinie (Ctrl+C pour arrêter)"
fi
echo "======================================"

# Créer le répertoire de sortie si nécessaire
mkdir -p "$(dirname "$OUTPUT")"

# Commande FFmpeg
if [ -n "$DURATION" ]; then
    ffmpeg -y -i "$SOURCE" -t "$DURATION" -vn -ar 44100 -ac 2 -f wav "$OUTPUT"
else
    ffmpeg -y -i "$SOURCE" -vn -ar 44100 -ac 2 -f wav "$OUTPUT"
fi

echo ""
echo "Enregistrement terminé: $OUTPUT"

