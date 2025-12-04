#!/bin/bash
# Script de déploiement pour Radio Occitania Pige System

set -e

echo "======================================"
echo "Radio Occitania - Déploiement"
echo "======================================"

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé"
    exit 1
fi

echo "✅ Docker et Docker Compose détectés"

# Vérifier le fichier .env
if [ ! -f .env ]; then
    echo "⚠️  Fichier .env non trouvé. Copie de .env.example..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Éditez le fichier .env avec vos paramètres !"
    read -p "Appuyez sur Entrée après avoir configuré .env..."
fi

echo ""
echo "🔨 Construction des images Docker..."
docker-compose build

echo ""
echo "🚀 Démarrage des services..."
docker-compose up -d

echo ""
echo "⏳ Attente du démarrage de la base de données..."
sleep 5

echo ""
echo "📦 Exécution des migrations..."
docker-compose exec web python manage.py migrate

echo ""
echo "👤 Création du superutilisateur..."
docker-compose exec web python manage.py createsuperuser --noinput || true

echo ""
echo "✅ Déploiement terminé !"
echo ""
echo "📍 Services disponibles:"
echo "   - API Django: http://localhost:8000"
echo "   - Admin: http://localhost:8000/admin"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "📝 Logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Arrêter:"
echo "   docker-compose down"

