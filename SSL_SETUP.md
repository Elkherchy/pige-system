# Configuration SSL avec Certbot pour pige.siraj-ai.com

## 📋 Prérequis

1. **DNS configuré** : Assurez-vous que le domaine `pige.siraj-ai.com` pointe vers l'IP de votre serveur
   ```bash
   # Vérifier la résolution DNS
   nslookup pige.siraj-ai.com
   dig pige.siraj-ai.com
   ```

2. **Ports ouverts** : Les ports 80 et 443 doivent être accessibles depuis Internet
   ```bash
   # Vérifier les ports
   sudo netstat -tlnp | grep -E ':(80|443)'
   ```

3. **Docker et Docker Compose** installés et fonctionnels

## 🚀 Installation et Configuration

### Étape 1 : Créer les répertoires pour Certbot

```bash
mkdir -p certbot/conf certbot/www
chmod -R 755 certbot
```

### Étape 2 : Démarrer les services (sans SSL pour la première fois)

```bash
# Construire et démarrer les conteneurs
docker-compose -f docker-compose.prod.yml up -d

# Vérifier que nginx fonctionne
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs nginx
```

### Étape 3 : Tester l'accès HTTP

Visitez http://pige.siraj-ai.com pour vérifier que le site est accessible.

### Étape 4 : Obtenir le certificat SSL avec Certbot

**Option A : Utilisation avec Docker (Recommandé)**

```bash
# Obtenir le certificat SSL
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email votre-email@exemple.com \
  --agree-tos \
  --no-eff-email \
  -d pige.siraj-ai.com

# Vérifier que les certificats ont été créés
ls -la certbot/conf/live/pige.siraj-ai.com/
```

**Option B : Installation directe sur le serveur**

```bash
# Installer Certbot (Ubuntu/Debian)
sudo apt update
sudo apt install certbot

# Obtenir le certificat
sudo certbot certonly --webroot \
  -w /chemin/vers/votre/projet/certbot/www \
  --email votre-email@exemple.com \
  --agree-tos \
  --no-eff-email \
  -d pige.siraj-ai.com
```

### Étape 5 : Activer la configuration HTTPS dans nginx

Une fois le certificat obtenu, éditez le fichier `nginx/conf.d/pige.conf` :

1. **Décommenter la configuration HTTPS** (lignes 72-155)
2. **Activer la redirection HTTP vers HTTPS** (ligne 15)

```bash
# Ouvrir le fichier pour modification
nano nginx/conf.d/pige.conf

# Décommenter la ligne suivante (ligne 15) :
return 301 https://$server_name$request_uri;

# Décommenter tout le bloc server HTTPS (lignes 72-155)
```

### Étape 6 : Redémarrer nginx

```bash
# Recharger la configuration nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# Ou redémarrer complètement
docker-compose -f docker-compose.prod.yml restart nginx
```

### Étape 7 : Vérifier l'installation SSL

1. Visitez https://pige.siraj-ai.com
2. Vérifiez le certificat dans votre navigateur (cadenas vert)
3. Testez avec SSL Labs : https://www.ssllabs.com/ssltest/analyze.html?d=pige.siraj-ai.com

## 🔄 Renouvellement Automatique

Le conteneur `certbot` dans docker-compose.prod.yml est configuré pour renouveler automatiquement les certificats tous les 12 heures.

### Tester le renouvellement manuellement

```bash
# Test de renouvellement (dry-run)
docker-compose -f docker-compose.prod.yml run --rm certbot renew --dry-run

# Renouvellement réel (si nécessaire)
docker-compose -f docker-compose.prod.yml run --rm certbot renew

# Recharger nginx après renouvellement
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### Vérifier l'expiration du certificat

```bash
# Vérifier la date d'expiration
docker-compose -f docker-compose.prod.yml run --rm certbot certificates

# Ou avec openssl
echo | openssl s_client -servername pige.siraj-ai.com -connect pige.siraj-ai.com:443 2>/dev/null | openssl x509 -noout -dates
```

## 🔧 Dépannage

### Problème : Certificat non trouvé

```bash
# Vérifier les logs de certbot
docker-compose -f docker-compose.prod.yml logs certbot

# Vérifier les permissions
ls -la certbot/conf/live/
```

### Problème : Nginx ne démarre pas après activation SSL

```bash
# Vérifier la configuration nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Vérifier les logs
docker-compose -f docker-compose.prod.yml logs nginx

# Revenir en arrière : recommenter la config HTTPS
nano nginx/conf.d/pige.conf
docker-compose -f docker-compose.prod.yml restart nginx
```

### Problème : Challenge ACME échoue

```bash
# Vérifier que /.well-known/acme-challenge/ est accessible
curl http://pige.siraj-ai.com/.well-known/acme-challenge/test

# Vérifier les permissions du répertoire
ls -la certbot/www/

# Vérifier la configuration DNS
dig pige.siraj-ai.com +short
```

### Problème : Certificat expiré

```bash
# Forcer le renouvellement
docker-compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal

# Recharger nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 📊 Monitoring des certificats

Configurez des alertes pour être notifié avant l'expiration :

```bash
# Créer un script de vérification
cat > check_ssl_expiry.sh << 'EOF'
#!/bin/bash
DOMAIN="pige.siraj-ai.com"
DAYS_UNTIL_EXPIRY=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -checkend $((30*86400)))

if [ $? -eq 0 ]; then
    echo "Certificate is valid for more than 30 days"
else
    echo "WARNING: Certificate expires in less than 30 days!"
    # Envoyer une notification par email ou autre
fi
EOF

chmod +x check_ssl_expiry.sh

# Ajouter à crontab pour vérification quotidienne
# crontab -e
# 0 9 * * * /chemin/vers/check_ssl_expiry.sh
```

## 🔒 Sécurité Avancée

### Configuration SSL renforcée (Déjà incluse)

La configuration nginx inclut déjà :
- ✅ TLS 1.2 et 1.3 uniquement
- ✅ Chiffrement moderne et sécurisé
- ✅ HSTS (HTTP Strict Transport Security)
- ✅ Session cache pour performance

### Vérifications de sécurité

```bash
# Tester la configuration SSL
testssl.sh https://pige.siraj-ai.com

# Ou utiliser nmap
nmap --script ssl-enum-ciphers -p 443 pige.siraj-ai.com
```

## 📝 Commandes Utiles

```bash
# Voir tous les certificats
docker-compose -f docker-compose.prod.yml run --rm certbot certificates

# Révoquer un certificat
docker-compose -f docker-compose.prod.yml run --rm certbot revoke --cert-path /etc/letsencrypt/live/pige.siraj-ai.com/cert.pem

# Supprimer un certificat
docker-compose -f docker-compose.prod.yml run --rm certbot delete --cert-name pige.siraj-ai.com

# Voir les logs nginx en temps réel
docker-compose -f docker-compose.prod.yml logs -f nginx

# Recharger la configuration sans downtime
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## ✅ Checklist de déploiement

- [ ] DNS configuré et propagé
- [ ] Ports 80 et 443 ouverts
- [ ] Répertoires certbot créés
- [ ] Services Docker démarrés
- [ ] Site accessible en HTTP
- [ ] Certificat SSL obtenu avec Certbot
- [ ] Configuration HTTPS activée dans nginx
- [ ] Redirection HTTP → HTTPS activée
- [ ] Site accessible en HTTPS
- [ ] Certificat vérifié sur SSL Labs
- [ ] Renouvellement automatique testé

## 📞 Support

En cas de problème :
1. Vérifier les logs : `docker-compose -f docker-compose.prod.yml logs`
2. Vérifier la documentation Certbot : https://certbot.eff.org/
3. Vérifier les logs nginx : `docker-compose -f docker-compose.prod.yml logs nginx`

