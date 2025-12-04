#!/bin/bash
# Script pour tester la disponibilité d'un stream

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <stream_url>"
    echo "Exemple: $0 http://stream.radio.com/live"
    exit 1
fi

STREAM_URL=$1

echo "======================================"
echo "Test de stream: $STREAM_URL"
echo "======================================"

ffmpeg -t 5 -i "$STREAM_URL" -f null - 2>&1 | grep -E "(Stream|Duration|time=)"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "✅ Stream accessible et fonctionnel"
    exit 0
else
    echo ""
    echo "❌ Stream inaccessible ou problème détecté"
    exit 1
fi

