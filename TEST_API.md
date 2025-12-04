# 🧪 Guide de Test API - Radio Occitania Pige System

## 🚀 Configuration Initiale

### Variables d'environnement
```bash
export API_URL="http://votre-serveur.com"  # ou http://localhost
export USERNAME="admin"
export PASSWORD="votre_mot_de_passe"
```

---

## 1️⃣ Tests de Base

### Vérifier que l'API répond
```bash
curl -X GET $API_URL/health
# Réponse attendue: OK
```

### Créer un superutilisateur (première fois)
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

---

## 2️⃣ Tests d'Authentification

### Obtenir l'utilisateur connecté
```bash
curl -X GET $API_URL/api/auth/users/me/ \
  -u $USERNAME:$PASSWORD
```

**Réponse attendue:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true
}
```

---

## 3️⃣ Tests Enregistrements

### Lister tous les enregistrements
```bash
curl -X GET $API_URL/api/archive/recordings/ \
  -u $USERNAME:$PASSWORD
```

### Vérifier un stream audio
```bash
curl -X POST $API_URL/api/recordings/check-stream/ \
  -u $USERNAME:$PASSWORD \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://stream.example.com/live"
  }'
```

**Réponse attendue:**
```json
{
  "url": "http://stream.example.com/live",
  "available": true,
  "error": null
}
```
### Démarrer un enregistrement
```bash
curl -X POST $API_URL/api/recordings/jobs/start/ \
  -u $USERNAME:$PASSWORD \
  -H "Content-Type: application/json" \
  -d '{
    "source": "http://stream.radio.com/live",
    "title": "Emission matinale",
    "format": "wav",
    "quality": "192k",
    "duration": 60,
    "template": "%text_%d-%m_%Hh%M"
  }'
```

**Réponse attendue:**
```json
{
  "success": true,
  "job_id": 1,
  "recording_id": 1,
  "process_id": 12345,
  "output_path": "/recordings/emission_04-12_14h30.wav",
  "message": "Enregistrement démarré"
}
```

### Lister les jobs actifs
```bash
curl -X GET $API_URL/api/recordings/jobs/active/ \
  -u $USERNAME:$PASSWORD
```

### Arrêter un enregistrement
```bash
curl -X POST $API_URL/api/recordings/jobs/stop/ \
  -u $USERNAME:$PASSWORD \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1
  }'
```

---

## 4️⃣ Tests Archive

### Détails d'un enregistrement
```bash
curl -X GET $API_URL/api/archive/recordings/1/ \
  -u $USERNAME:$PASSWORD
```

### Télécharger un enregistrement
```bash
curl -X GET $API_URL/api/archive/recordings/1/download/ \
  -u $USERNAME:$PASSWORD \
  -o recording.wav
```

### Traiter un enregistrement (transcription + résumé)
```bash
curl -X POST $API_URL/api/archive/recordings/1/process/ \
  -u $USERNAME:$PASSWORD
```

### Prolonger la rétention
```bash
curl -X POST $API_URL/api/archive/recordings/1/extend_retention/ \
  -u $USERNAME:$PASSWORD \
  -H "Content-Type: application/json" \
  -d '{
    "days": 30
  }'
```

### Statistiques globales
```bash
curl -X GET $API_URL/api/archive/recordings/statistics/ \
  -u $USERNAME:$PASSWORD
```

**Réponse attendue:**
```json
{
  "total_recordings": 45,
  "by_status": {
    "completed": 40,
    "processing": 2,
    "recording": 1,
    "error": 2
  },
  "flagged_blanks": 8,
  "total_duration": 162000.5,
  "avg_duration": 3600.0,
  "total_size": 13743895347
}
```

---

## 5️⃣ Tests Alertes de Blanc

### Lister toutes les alertes
```bash
curl -X GET $API_URL/api/archive/alerts/ \
  -u $USERNAME:$PASSWORD
```

### Filtrer les alertes critiques
```bash
curl -X GET "$API_URL/api/archive/alerts/?severity=critical" \
  -u $USERNAME:$PASSWORD
```

### Marquer un blanc comme naturel
```bash
curl -X POST $API_URL/api/archive/alerts/1/mark_as_natural/ \
  -u $USERNAME:$PASSWORD
```

---

## 6️⃣ Tests IA

### Informations sur les modèles
```bash
curl -X GET $API_URL/api/ai/models-info/ \
  -u $USERNAME:$PASSWORD
```

**Réponse attendue:**
```json
{
  "whisper": {
    "available": false,
    "message": "Whisper non installé"
  },
  "mistral": {
    "model": "mistral-small-latest",
    "provider": "Mistral AI API",
    "api_key_configured": true
  }
}
```

### Transcrire un enregistrement
```bash
curl -X POST $API_URL/api/ai/transcribe/ \
  -u $USERNAME:$PASSWORD \
  -H "Content-Type: application/json" \
  -d '{
    "recording_id": 1,
    "language": "fr"
  }'
```

### Générer un résumé
```bash
curl -X POST $API_URL/api/ai/summarize/ \
  -u $USERNAME:$PASSWORD \
  -H "Content-Type: application/json" \
  -d '{
    "recording_id": 1,
    "max_sentences": 5
  }'
```

### Extraire les mots-clés
```bash
curl -X POST $API_URL/api/ai/extract-keywords/ \
  -u $USERNAME:$PASSWORD \
  -H "Content-Type: application/json" \
  -d '{
    "recording_id": 1,
    "max_keywords": 10
  }'
```

---

## 7️⃣ Tests de Recherche et Filtrage

### Recherche full-text
```bash
curl -X GET "$API_URL/api/archive/recordings/?search=emission" \
  -u $USERNAME:$PASSWORD
```

### Filtrer par statut
```bash
curl -X GET "$API_URL/api/archive/recordings/?status=completed" \
  -u $USERNAME:$PASSWORD
```

### Filtrer les enregistrements avec blancs
```bash
curl -X GET "$API_URL/api/archive/recordings/?flagged_blank=true" \
  -u $USERNAME:$PASSWORD
```

### Tri et pagination
```bash
curl -X GET "$API_URL/api/archive/recordings/?ordering=-created_at&page=1&page_size=10" \
  -u $USERNAME:$PASSWORD
```

---

## 8️⃣ Script de Test Complet

Créez `test_complet.sh`:

```bash
#!/bin/bash

# Configuration
API_URL="http://localhost"
USERNAME="admin"
PASSWORD="password"

echo "🧪 Tests Système de Pige - Radio Occitania"
echo "=========================================="

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Fonction de test
test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    local data=$4
    
    echo -e "\n${YELLOW}Test: $name${NC}"
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$API_URL$url" -u $USERNAME:$PASSWORD)
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$API_URL$url" \
            -u $USERNAME:$PASSWORD \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
        echo -e "${GREEN}✅ OK ($http_code)${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ ERREUR ($http_code)${NC}"
        echo "$body"
    fi
}

# Tests
test_endpoint "1. Health Check" "/health"
test_endpoint "2. Utilisateur connecté" "/api/auth/users/me/"
test_endpoint "3. Liste enregistrements" "/api/archive/recordings/"
test_endpoint "4. Statistiques" "/api/archive/recordings/statistics/"
test_endpoint "5. Liste alertes" "/api/archive/alerts/"
test_endpoint "6. Info modèles IA" "/api/ai/models-info/"

echo -e "\n${GREEN}=========================================="
echo "Tests terminés !"
echo -e "==========================================${NC}"
```

Lancez-le:
```bash
chmod +x test_complet.sh
./test_complet.sh
```

---

## 9️⃣ Tests de Performance

### Créer 10 enregistrements en parallèle
```bash
for i in {1..10}; do
  curl -X POST $API_URL/api/recordings/jobs/start/ \
    -u $USERNAME:$PASSWORD \
    -H "Content-Type: application/json" \
    -d "{
      \"source\": \"http://stream.radio.com/live\",
      \"title\": \"Test $i\",
      \"duration\": 10
    }" &
done
wait
```

### Vérifier la charge
```bash
curl -X GET $API_URL/api/recordings/jobs/active/ \
  -u $USERNAME:$PASSWORD
```

---

## 🔟 Tests d'Erreurs

### Stream invalide
```bash
curl -X POST $API_URL/api/recordings/check-stream/ \
  -u $USERNAME:$PASSWORD \
  -H "Content-Type: application/json" \
  -d '{"url": "http://invalid-stream.com/404"}'
```

### Enregistrement inexistant
```bash
curl -X GET $API_URL/api/archive/recordings/99999/ \
  -u $USERNAME:$PASSWORD
```

### Authentification invalide
```bash
curl -X GET $API_URL/api/archive/recordings/ \
  -u wrong:credentials
```

---

## 📊 Monitoring

### Logs en temps réel
```bash
# Logs Nginx
docker-compose -f docker-compose.prod.yml logs -f nginx

# Logs Django
docker-compose -f docker-compose.prod.yml logs -f web

# Logs Celery
docker-compose -f docker-compose.prod.yml logs -f worker
```

### État des services
```bash
docker-compose -f docker-compose.prod.yml ps
```

---

## ✅ Checklist de Production

- [ ] Tous les services démarrent correctement
- [ ] API répond sur /health
- [ ] Admin accessible
- [ ] Enregistrement test réussi
- [ ] Transcription fonctionne (si configurée)
- [ ] Résumé fonctionne (Mistral API)
- [ ] Alertes email configurées
- [ ] Logs accessibles
- [ ] Backup configuré

**Système prêt pour la production ! 🚀**

