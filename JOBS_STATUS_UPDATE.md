# Mise à jour automatique du statut des jobs

## 🎯 Problème résolu

Les jobs d'enregistrement restaient en statut "En cours" même lorsque les processus (PIDs) étaient terminés. Le backend ne vérifiait pas automatiquement l'état réel des processus.

## ✅ Solution implémentée

### 1. Nouvelle fonction : `is_process_running()`

**Fichier :** `apps/recorder/services.py`

```python
def is_process_running(process_id):
    """
    Vérifie si un processus est en cours d'exécution
    
    Returns:
        bool: True si le processus est actif, False sinon
    """
```

Cette fonction vérifie si un PID est toujours actif en utilisant `os.kill(pid, 0)`.

### 2. Mise à jour automatique dans `GET /api/recordings/jobs/active/`

**Comportement :**
- Récupère tous les jobs avec statut `running`
- Vérifie pour chaque job si le processus (PID) est toujours actif
- **Si le processus n'est plus actif :**
  - ✅ Met à jour le statut du job à `completed`
  - ✅ Ajoute la date `completed_at`
  - ✅ Met à jour le recording associé en statut `processing`
  - ✅ Lance le traitement automatique (transcription, analyse)

### 3. Nouvel endpoint : `POST /api/recordings/jobs/cleanup/`

Permet de nettoyer manuellement TOUS les jobs obsolètes d'un seul coup.

**Réponse :**
```json
{
  "success": true,
  "updated_count": 4,
  "message": "4 job(s) mis à jour"
}
```

---

## 📚 Utilisation

### Option 1 : Mise à jour automatique (recommandé)

Le frontend appelle régulièrement `GET /api/recordings/jobs/active/` :

```typescript
// Dans votre composant React/Next.js
useEffect(() => {
  const interval = setInterval(async () => {
    const response = await fetch('/api/recordings/jobs/active/');
    const data = await response.json();
    setActiveJobs(data.jobs);
  }, 5000); // Toutes les 5 secondes
  
  return () => clearInterval(interval);
}, []);
```

**Avantage :** Les jobs obsolètes sont automatiquement nettoyés à chaque appel.

### Option 2 : Nettoyage manuel

Ajouter un bouton "Actualiser" ou "Nettoyer" :

```typescript
const cleanupJobs = async () => {
  const response = await fetch('/api/recordings/jobs/cleanup/', {
    method: 'POST'
  });
  const data = await response.json();
  console.log(`${data.updated_count} job(s) mis à jour`);
};
```

### Option 3 : Via cURL (test/debug)

```bash
# Lister les jobs actifs (nettoie automatiquement)
curl http://localhost:8000/api/recordings/jobs/active/

# Nettoyer manuellement tous les jobs
curl -X POST http://localhost:8000/api/recordings/jobs/cleanup/
```

---

## 🔧 Endpoints disponibles

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/recordings/jobs/active/` | Liste les jobs actifs + nettoyage automatique |
| POST | `/api/recordings/jobs/cleanup/` | Nettoie tous les jobs obsolètes |
| POST | `/api/recordings/jobs/start/` | Démarre un enregistrement |
| POST | `/api/recordings/jobs/stop/` | Arrête un job (body: `job_id`) |

---

## 🎬 Exemple complet

### Problème initial

```
Job #4 - PID: 33 - Statut: En cours
Job #3 - PID: 73 - Statut: En cours
Job #2 - PID: 53 - Statut: En cours
Job #1 - PID: 24 - Statut: En cours
```

**Mais les processus 33, 73, 53, 24 n'existent plus !**

### Solution

**1. Appeler le endpoint de nettoyage :**

```bash
curl -X POST http://localhost:8000/api/recordings/jobs/cleanup/
```

**Réponse :**
```json
{
  "success": true,
  "updated_count": 4,
  "message": "4 job(s) mis à jour"
}
```

**2. Vérifier les jobs actifs :**

```bash
curl http://localhost:8000/api/recordings/jobs/active/
```

**Réponse :**
```json
{
  "count": 0,
  "jobs": []
}
```

✅ Tous les jobs obsolètes ont été nettoyés automatiquement !

---

## 🔄 Workflow complet

```
1. Utilisateur démarre un enregistrement
   ↓
2. Job créé avec statut "running" + PID
   ↓
3. Frontend affiche "En cours..."
   ↓
4. Enregistrement se termine (processus s'arrête)
   ↓
5. Frontend appelle GET /api/recordings/jobs/active/
   ↓
6. Backend détecte que le PID n'est plus actif
   ↓
7. Backend met à jour :
   - Job → statut "completed"
   - Recording → statut "processing"
   - Lance le traitement automatique
   ↓
8. Frontend reçoit la liste mise à jour (job n'est plus dans la liste)
   ↓
9. Frontend met à jour l'affichage
```

---

## 🚀 Déploiement

Aucune configuration supplémentaire requise ! Les modifications sont déjà en place.

Pour appliquer les changements :

```bash
# 1. Rebuilder le conteneur
docker-compose up --build -d

# 2. (Optionnel) Nettoyer les jobs obsolètes actuels
curl -X POST http://localhost:8000/api/recordings/jobs/cleanup/
```

---

## 💡 Recommandations

### Pour le frontend

1. **Polling régulier** : Appelez `/api/recordings/jobs/active/` toutes les 5-10 secondes
2. **Bouton de rafraîchissement** : Permettre un nettoyage manuel via `/api/recordings/jobs/cleanup/`
3. **Indicateur visuel** : Afficher le nombre de jobs actifs mis à jour en temps réel

### Pour le backend

Les jobs sont maintenant automatiquement nettoyés. Vous pouvez aussi créer une tâche Celery périodique pour un nettoyage automatique :

```python
# Dans apps/recorder/tasks.py (à créer)
from celery import shared_task
from .models import RecordingJob
from .services import is_process_running

@shared_task
def cleanup_stale_jobs():
    """Nettoie automatiquement les jobs obsolètes toutes les minutes"""
    running_jobs = RecordingJob.objects.filter(status='running')
    for job in running_jobs:
        if not job.process_id or not is_process_running(job.process_id):
            job.status = 'completed'
            job.save()
```

---

## 📋 Résumé

✅ **Problème résolu** : Les jobs restent "En cours" même quand terminés  
✅ **Solution** : Vérification automatique de l'état réel des processus  
✅ **Endpoints** : `/active/` (auto-nettoyage) + `/cleanup/` (nettoyage manuel)  
✅ **Impact** : Frontend affiche maintenant l'état réel des jobs en temps réel  

**Résultat :** Votre système affiche maintenant correctement l'état des enregistrements ! 🎉

