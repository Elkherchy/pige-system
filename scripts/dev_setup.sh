#!/bin/bash
# Script de setup pour le développement local (sans Docker)

set -e

echo "======================================"
echo "Radio Occitania - Setup Développement"
echo "======================================"

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

# Créer un environnement virtuel
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

echo "🔄 Activation de l'environnement virtuel..."
source venv/bin/activate

echo "📦 Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

# Vérifier FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg n'est pas installé. Installez-le avec:"
    echo "   - macOS: brew install ffmpeg"
    echo "   - Ubuntu: sudo apt install ffmpeg"
    echo "   - Windows: Téléchargez depuis ffmpeg.org"
fi

# Copier .env si nécessaire
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Fichier .env créé. Configurez-le selon vos besoins."
fi

echo ""
echo "📊 Migrations de la base de données..."
python manage.py makemigrations
python manage.py migrate

echo ""
echo "👤 Création du superutilisateur..."
python manage.py createsuperuser

echo ""
echo "✅ Setup terminé !"
echo ""
echo "🚀 Pour lancer le serveur de développement:"
echo "   source venv/bin/activate"
echo "   python manage.py runserver"
echo ""
echo "📝 Pour lancer Celery (terminal séparé):"
echo "   celery -A config.celery_app worker --loglevel=info"

