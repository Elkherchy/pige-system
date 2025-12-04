# 🏗️ Architecture - Radio Occitania Pige System

Documentation technique de l'architecture du système.

---

## 📐 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                     Radio Occitania Pige                     │
│                   Système d'Enregistrement                   │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Streams    │─────▶│   Recorder   │─────▶│   Archive    │
│ Audio/Radio  │      │    (FFmpeg)  │      │  (Storage)   │
└──────────────┘      └──────────────┘      └──────────────┘
                             │                      │
                             ▼                      ▼
                      ┌──────────────┐      ┌──────────────┐
                      │   Celery     │─────▶│      IA      │
                      │   Workers    │      │ Whisper +    │
                      └──────────────┘      │   Mistral    │
                             │              └──────────────┘
                             ▼                      │
                      ┌──────────────┐              │
                      │  PostgreSQL  │◀─────────────┘
                      │     DB       │
                      └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │   Django     │
                      │   REST API   │
                      └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │   Frontend   │
                      │  (Futur)     │
                      └──────────────┘
```

---

## 🔧 Stack Technique

### Backend
- **Framework** : Django 4.2+
- **API** : Django REST Framework
- **Database** : PostgreSQL 15
- **Cache** : Redis 7
- **Task Queue** : Celery + Redis

### Audio Processing
- **Enregistrement** : FFmpeg
- **Détection Silence** : FFmpeg silencedetect
- **Formats** : WAV, MP3, FLAC

### Intelligence Artificielle
- **Transcription** : OpenAI Whisper (local)
- **Résumé/Analyse** : Mistral 7B via Ollama (local)
- **Device** : CPU ou GPU (CUDA)

### Infrastructure
- **Conteneurisation** : Docker + Docker Compose
- **Web Server** : Gunicorn + Nginx
- **SSL** : Let's Encrypt

---

## 📦 Applications Django

### 1. `accounts` - Authentification

**Responsabilités :**
- Gestion des utilisateurs
- Rôles (admin, operator, viewer)
- Authentification API

**Modèles :**
- `User` (AbstractUser personnalisé)

**Endpoints :**
- `/api/auth/users/`
- `/api/auth/users/me/`
- `/api/auth/users/change_password/`

---

### 2. `recorder` - Enregistrement

**Responsabilités :**
- Orchestration FFmpeg
- Gestion des jobs d'enregistrement
- Vérification santé des streams
- Monitoring espace disque

**Modèles :**
- `RecordingJob`

**Services :**
- `start_record()` - Démarre un enregistrement
- `stop_record()` - Arrête un enregistrement
- `detect_silence_ffmpeg()` - Détecte les silences
- `get_audio_metadata()` - Extrait les métadonnées
- `check_stream_health()` - Vérifie un stream
- `build_filename()` - Génère les noms de fichiers

**Endpoints :**
- `/api/recordings/jobs/start/`
- `/api/recordings/jobs/stop/`
- `/api/recordings/jobs/active/`
- `/api/recordings/check-stream/`

**Tasks Celery :**
- `check_storage_health` - Monitoring disque (30 min)
- `cleanup_failed_jobs` - Nettoyage jobs (quotidien)

---

### 3. `archive` - Gestion Archives

**Responsabilités :**
- Stockage des enregistrements
- Métadonnées audio
- Gestion rétention
- Alertes de blanc

**Modèles :**
- `Recording` - Enregistrement principal
- `BlankAlert` - Alerte de silence

**Endpoints :**
- `/api/archive/recordings/` (CRUD)
- `/api/archive/recordings/{id}/download/`
- `/api/archive/recordings/{id}/process/`
- `/api/archive/recordings/statistics/`
- `/api/archive/alerts/`

**Tasks Celery :**
- `process_recording` - Traitement complet (transcription + analyse)
- `cleanup_expired_files` - Suppression fichiers expirés (quotidien)

---

### 4. `ai` - Intelligence Artificielle

**Responsabilités :**
- Transcription audio → texte
- Résumé de texte
- Extraction mots-clés
- Analyse contextuelle des blancs

**Services :**
- **whisper_service.py**
  - `transcribe_file()` - Transcription complète
  - `transcribe_segment()` - Transcription d'un segment
  
- **mistral_service.py**
  - `summarize_text()` - Génère un résumé
  - `analyze_blank_context()` - Analyse un blanc
  - `extract_keywords()` - Extrait les mots-clés
  - `call_ollama()` - Interface Ollama

**Endpoints :**
- `/api/ai/transcribe/`
- `/api/ai/summarize/`
- `/api/ai/extract-keywords/`
- `/api/ai/models-info/`

---

## 🔄 Flux de Données

### 1. Enregistrement

```
1. Client ──POST /jobs/start/──▶ Recorder API
                                       │
2.                          start_record(FFmpeg)
                                       │
3.                              RecordingJob ───▶ DB
                                       │
4.                              Recording ─────▶ DB
                                       │
5. FFmpeg Process ─────▶ Fichier WAV/MP3
```

### 2. Traitement Automatique

```
1. Recording terminé ──▶ process_recording.delay()
                                │
2.               detect_silence_ffmpeg()
                                │
3.              BlankAlert ────▶ DB (si détecté)
                                │
4.               transcribe_file() ───▶ Whisper
                                │
5.              Recording.transcript ▶ DB
                                │
6.         analyze_blank_context() ──▶ Mistral
                                │
7.              BlankAlert.ai_* ─────▶ DB
                                │
8.               summarize_text() ───▶ Mistral
                                │
9.              Recording.summary ───▶ DB
                                │
10.        Notification email (si blanc suspect)
```

### 3. Détection de Blanc

```
1. FFmpeg silencedetect ──▶ Liste (start, end)
                                │
2.               Pour chaque blanc > 5s:
                                │
3.              Créer BlankAlert ─────▶ DB
                                │
4.              Extraire contexte (-5s, +5s)
                                │
5.              Transcrire segments ──▶ Whisper
                                │
6.              Analyser avec Mistral
                                │
7.     Classification: Naturel / Suspect
                                │
8.              Si suspect ──▶ Email notification
```

---

## 🗄️ Schéma Base de Données

### Modèle `User`
```
users
├── id (PK)
├── username
├── email
├── password (hashed)
├── first_name
├── last_name
├── role (admin/operator/viewer)
├── phone
├── notifications_enabled
└── date_joined
```

### Modèle `Recording`
```
recordings
├── id (PK)
├── title
├── filename
├── filepath
├── duration
├── format
├── bitrate
├── sample_rate
├── channels
├── file_size
├── status (recording/processing/completed/error)
├── flagged_blank
├── blank_analysis (JSON)
├── transcript (TEXT)
├── summary (TEXT)
├── ai_metadata (JSON)
├── owner_id (FK → users)
├── created_at
├── updated_at
├── expires_at
├── tags (JSON)
└── notes
```

### Modèle `BlankAlert`
```
blank_alerts
├── id (PK)
├── recording_id (FK → recordings)
├── start_time
├── end_time
├── duration
├── severity (info/warning/critical)
├── is_natural
├── ai_confidence
├── ai_explanation
├── notified
└── created_at
```

### Modèle `RecordingJob`
```
recording_jobs
├── id (PK)
├── source_url
├── output_path
├── format
├── quality
├── duration
├── status (scheduled/running/stopped/completed/failed)
├── process_id
├── created_at
├── started_at
├── completed_at
└── error_message
```

---

## ⚙️ Configuration Celery

### Workers
- **Concurrency** : 2 workers par défaut
- **Timeout** : 30 minutes par tâche
- **Broker** : Redis
- **Backend** : Redis

### Tâches Périodiques (Celery Beat)

| Tâche | Fréquence | Description |
|-------|-----------|-------------|
| `cleanup_expired_files` | Quotidien 3h | Supprime les fichiers expirés |
| `check_storage_health` | 30 min | Vérifie l'espace disque |
| `cleanup_failed_jobs` | Quotidien 4h | Nettoie les jobs échoués |

---

## 🔐 Sécurité

### Authentification
- HTTP Basic Auth
- Session Auth (pour browsable API)
- Permissions par rôle

### Autorisation
```python
# Permissions
- IsAuthenticated (requis pour toutes les API)
- Role-based: admin, operator, viewer

# Vérifications
User.can_manage_recordings() → admin, operator
User.can_view_analytics() → tous
```

### Données Sensibles
- Mots de passe : hachés (PBKDF2)
- Secrets : variables d'environnement (.env)
- Fichiers media : authentification Nginx
- Logs : accès restreint

### CORS
- Configurable via `CORS_ORIGINS`
- Désactivé par défaut en production

---

## 📊 Performance

### Optimisations

**Base de données :**
- Index sur `created_at`, `status`, `flagged_blank`
- Select_related / Prefetch_related dans les vues
- Pagination (50 éléments par défaut)

**API :**
- Serializers légers pour les listes
- Serializers complets pour les détails
- Cache potentiel avec Redis

**Storage :**
- Fichiers hors DB (filesystem)
- Chemin configurable
- Nettoyage automatique

**Celery :**
- Tâches asynchrones pour opérations longues
- Retry automatique sur échec
- Rate limiting possible

---

## 🧪 Tests

### Tests Unitaires
```bash
python manage.py test apps.accounts
python manage.py test apps.recorder
python manage.py test apps.archive
python manage.py test apps.ai
```

### Tests d'Intégration
```bash
python manage.py test --tag=integration
```

### Tests de Performance
```bash
locust -f locustfile.py
```

---

## 📈 Monitoring

### Métriques Clés

**Système :**
- Utilisation CPU / RAM
- Espace disque
- Latence réseau

**Application :**
- Nombre d'enregistrements actifs
- Durée moyenne de traitement
- Taux d'erreur
- Queue Celery

**Business :**
- Enregistrements par jour
- Blancs détectés
- Alertes envoyées
- Espace de stockage utilisé

### Endpoints de Santé

```
GET /api/archive/recordings/statistics/
- Total enregistrements
- Par statut
- Espace utilisé
- Durée totale

GET /api/recordings/jobs/active/
- Jobs en cours
- PIDs processus
```

---

## 🔄 CI/CD (Futur)

### Pipeline Proposé

```yaml
stages:
  - test
  - build
  - deploy

test:
  - python manage.py test
  - flake8
  - black --check

build:
  - docker build -t pige:latest .

deploy:
  - ssh production "cd /home/pige && git pull && docker-compose up -d"
```

---

## 🚀 Évolutions Futures

### Court Terme
- [ ] Interface web (React/Vue.js)
- [ ] API webhooks
- [ ] Export cloud (S3)
- [ ] Calendrier enregistrements programmés

### Moyen Terme
- [ ] Multi-stream simultané
- [ ] Détection musique vs voix
- [ ] Tableau de bord temps réel
- [ ] Application mobile

### Long Terme
- [ ] Machine Learning custom
- [ ] Reconnaissance vocale (speakers)
- [ ] Génération automatique de podcasts
- [ ] Analyse sentiment

---

## 📚 Ressources

### Documentation
- [README.md](README.md) - Guide principal
- [QUICKSTART.md](QUICKSTART.md) - Démarrage rapide
- [API.md](API.md) - Documentation API
- [PRODUCTION.md](PRODUCTION.md) - Déploiement production

### Dépendances
- [Django](https://docs.djangoproject.com/)
- [DRF](https://www.django-rest-framework.org/)
- [Celery](https://docs.celeryq.dev/)
- [FFmpeg](https://ffmpeg.org/documentation.html)
- [Whisper](https://github.com/openai/whisper)
- [Ollama](https://ollama.ai/docs)

---

**Architecture solide et scalable ! 🏗️**

