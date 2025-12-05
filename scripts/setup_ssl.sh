#!/bin/bash

# Script d'installation SSL avec Certbot pour pige.siraj-ai.com
# Usage: ./scripts/setup_ssl.sh [email]

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="pige.siraj-ai.com"
EMAIL=${1:-""}
COMPOSE_FILE="docker-compose.prod.yml"

echo -e "${GREEN}🔐 Configuration SSL pour ${DOMAIN}${NC}\n"

# Fonction pour vérifier les prérequis
check_prerequisites() {
    echo -e "${YELLOW}📋 Vérification des prérequis...${NC}"
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker n'est pas installé${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker installé${NC}"
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose n'est pas installé${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker Compose installé${NC}"
    
    # Vérifier la résolution DNS
    echo -e "${YELLOW}🌐 Vérification DNS pour ${DOMAIN}...${NC}"
    if ! host ${DOMAIN} > /dev/null 2>&1; then
        echo -e "${RED}❌ Le domaine ${DOMAIN} ne peut pas être résolu${NC}"
        echo -e "${YELLOW}⚠️  Assurez-vous que le DNS est configuré correctement${NC}"
        read -p "Voulez-vous continuer quand même ? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}✅ DNS configuré correctement${NC}"
        IP=$(dig +short ${DOMAIN} | tail -1)
        echo -e "${GREEN}   IP: ${IP}${NC}"
    fi
    
    # Demander l'email si non fourni
    if [ -z "$EMAIL" ]; then
        echo
        read -p "Entrez votre adresse email pour Let's Encrypt: " EMAIL
        if [ -z "$EMAIL" ]; then
            echo -e "${RED}❌ L'email est requis${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}✅ Email: ${EMAIL}${NC}\n"
}

# Créer les répertoires nécessaires
create_directories() {
    echo -e "${YELLOW}📁 Création des répertoires...${NC}"
    mkdir -p certbot/conf certbot/www
    chmod -R 755 certbot
    echo -e "${GREEN}✅ Répertoires créés${NC}\n"
}

# Démarrer les services
start_services() {
    echo -e "${YELLOW}🚀 Démarrage des services Docker...${NC}"
    docker-compose -f ${COMPOSE_FILE} up -d
    
    # Attendre que nginx soit prêt
    echo -e "${YELLOW}⏳ Attente du démarrage de nginx...${NC}"
    sleep 5
    
    # Vérifier que nginx fonctionne
    if ! docker-compose -f ${COMPOSE_FILE} ps | grep -q "nginx.*Up"; then
        echo -e "${RED}❌ Nginx n'a pas démarré correctement${NC}"
        docker-compose -f ${COMPOSE_FILE} logs nginx
        exit 1
    fi
    echo -e "${GREEN}✅ Services démarrés${NC}\n"
}

# Tester l'accès HTTP
test_http() {
    echo -e "${YELLOW}🌐 Test de l'accès HTTP...${NC}"
    if curl -s -o /dev/null -w "%{http_code}" http://${DOMAIN}/health | grep -q "200"; then
        echo -e "${GREEN}✅ Site accessible en HTTP${NC}\n"
    else
        echo -e "${YELLOW}⚠️  Le site n'est pas encore accessible${NC}"
        echo -e "${YELLOW}   Assurez-vous que le port 80 est ouvert${NC}\n"
    fi
}

# Obtenir le certificat SSL
obtain_certificate() {
    echo -e "${YELLOW}🔐 Obtention du certificat SSL...${NC}"
    echo -e "${YELLOW}   Cela peut prendre quelques minutes...${NC}\n"
    
    # Obtenir le certificat avec Certbot
    if docker-compose -f ${COMPOSE_FILE} run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email ${EMAIL} \
        --agree-tos \
        --no-eff-email \
        -d ${DOMAIN}; then
        echo -e "\n${GREEN}✅ Certificat SSL obtenu avec succès !${NC}\n"
    else
        echo -e "\n${RED}❌ Échec de l'obtention du certificat SSL${NC}"
        echo -e "${YELLOW}💡 Vérifiez que :${NC}"
        echo -e "   - Le domaine ${DOMAIN} pointe vers ce serveur"
        echo -e "   - Le port 80 est accessible depuis Internet"
        echo -e "   - Le fichier nginx/conf.d/pige.conf est correct"
        exit 1
    fi
    
    # Vérifier les certificats
    ls -la certbot/conf/live/${DOMAIN}/
}

# Activer HTTPS dans nginx
enable_https() {
    echo -e "${YELLOW}🔧 Configuration de HTTPS dans nginx...${NC}"
    
    CONFIG_FILE="nginx/conf.d/pige.conf"
    
    # Créer une sauvegarde
    cp ${CONFIG_FILE} ${CONFIG_FILE}.bak
    echo -e "${GREEN}✅ Sauvegarde créée: ${CONFIG_FILE}.bak${NC}"
    
    # Décommenter la redirection HTTP vers HTTPS
    sed -i.tmp 's/# return 301 https/return 301 https/' ${CONFIG_FILE}
    
    # Décommenter le bloc HTTPS (supprimer les # au début des lignes du bloc HTTPS)
    # Cette partie est un peu complexe car nous devons décommenter un bloc spécifique
    awk '
        /^# Configuration HTTPS avec Let/ { in_https=1 }
        in_https && /^# server {/ { in_server=1; print "server {"; next }
        in_https && in_server && /^# }$/ { in_server=0; in_https=0; print "}"; next }
        in_https && in_server && /^#/ { sub(/^# /, ""); sub(/^#$/, ""); print; next }
        { print }
    ' ${CONFIG_FILE} > ${CONFIG_FILE}.new
    
    mv ${CONFIG_FILE}.new ${CONFIG_FILE}
    rm -f ${CONFIG_FILE}.tmp
    
    echo -e "${GREEN}✅ Configuration HTTPS activée${NC}\n"
}

# Recharger nginx
reload_nginx() {
    echo -e "${YELLOW}🔄 Rechargement de nginx...${NC}"
    
    # Tester la configuration
    if docker-compose -f ${COMPOSE_FILE} exec nginx nginx -t; then
        echo -e "${GREEN}✅ Configuration nginx valide${NC}"
        
        # Recharger nginx
        docker-compose -f ${COMPOSE_FILE} exec nginx nginx -s reload
        echo -e "${GREEN}✅ Nginx rechargé${NC}\n"
    else
        echo -e "${RED}❌ Configuration nginx invalide${NC}"
        echo -e "${YELLOW}⚠️  Restauration de la configuration précédente...${NC}"
        cp ${CONFIG_FILE}.bak ${CONFIG_FILE}
        docker-compose -f ${COMPOSE_FILE} restart nginx
        exit 1
    fi
}

# Vérifier HTTPS
verify_https() {
    echo -e "${YELLOW}🔍 Vérification de HTTPS...${NC}"
    sleep 3
    
    if curl -s -o /dev/null -w "%{http_code}" https://${DOMAIN}/health | grep -q "200"; then
        echo -e "${GREEN}✅ HTTPS fonctionne correctement !${NC}"
        echo -e "${GREEN}🎉 Votre site est maintenant accessible sur https://${DOMAIN}${NC}\n"
    else
        echo -e "${YELLOW}⚠️  HTTPS ne répond pas encore${NC}"
        echo -e "${YELLOW}   Vérifiez manuellement : https://${DOMAIN}${NC}\n"
    fi
}

# Afficher les informations finales
show_info() {
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Installation SSL terminée avec succès !${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${YELLOW}📊 Informations sur le certificat :${NC}"
    docker-compose -f ${COMPOSE_FILE} run --rm certbot certificates
    
    echo -e "\n${YELLOW}🔗 URLs :${NC}"
    echo -e "   HTTP  : http://${DOMAIN} (redirige vers HTTPS)"
    echo -e "   HTTPS : https://${DOMAIN}"
    echo -e "   Health: https://${DOMAIN}/health"
    
    echo -e "\n${YELLOW}📝 Commandes utiles :${NC}"
    echo -e "   Renouveler le certificat :"
    echo -e "   ${GREEN}docker-compose -f ${COMPOSE_FILE} run --rm certbot renew${NC}"
    echo -e "\n   Voir les certificats :"
    echo -e "   ${GREEN}docker-compose -f ${COMPOSE_FILE} run --rm certbot certificates${NC}"
    echo -e "\n   Recharger nginx :"
    echo -e "   ${GREEN}docker-compose -f ${COMPOSE_FILE} exec nginx nginx -s reload${NC}"
    
    echo -e "\n${YELLOW}🔄 Renouvellement automatique :${NC}"
    echo -e "   Le certificat sera automatiquement renouvelé tous les 12h"
    
    echo -e "\n${YELLOW}🔒 Vérifier la sécurité SSL :${NC}"
    echo -e "   https://www.ssllabs.com/ssltest/analyze.html?d=${DOMAIN}"
    
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Menu principal
main() {
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}     Installation SSL automatique avec Let's Encrypt${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    check_prerequisites
    create_directories
    start_services
    test_http
    obtain_certificate
    enable_https
    reload_nginx
    verify_https
    show_info
}

# Exécuter le script
main

