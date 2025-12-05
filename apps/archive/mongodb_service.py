"""
Service pour la gestion du stockage MongoDB avec GridFS
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pymongo import MongoClient
from gridfs import GridFS
from django.conf import settings

logger = logging.getLogger(__name__)


class MongoDBService:
    """
    Service pour gérer le stockage des fichiers audio dans MongoDB via GridFS
    """
    
    def __init__(self):
        """Initialise la connexion MongoDB"""
        self.client = None
        self.db = None
        self.fs = None
        self._connect()
    
    def _connect(self):
        """Établit la connexion à MongoDB"""
        try:
            self.client = MongoClient(settings.MONGODB_URI)
            self.db = self.client[settings.MONGODB_DATABASE]
            self.fs = GridFS(self.db)
            # Test de connexion
            self.client.admin.command('ping')
            logger.info("✓ Connexion MongoDB établie")
        except Exception as e:
            logger.error(f"✗ Erreur de connexion MongoDB: {e}")
            raise
    
    def upload_file(
        self,
        file_path: str,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload un fichier vers MongoDB GridFS
        
        Args:
            file_path: Chemin vers le fichier à uploader
            filename: Nom du fichier (par défaut: nom du fichier original)
            metadata: Métadonnées additionnelles
        
        Returns:
            Dict contenant file_id et url
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Fichier introuvable: {file_path}")
            
            # Préparer les métadonnées
            if filename is None:
                filename = os.path.basename(file_path)
            
            file_metadata = {
                'filename': filename,
                'upload_date': datetime.utcnow(),
                'content_type': self._get_content_type(filename),
            }
            
            if metadata:
                file_metadata.update(metadata)
            
            # Lire et uploader le fichier
            with open(file_path, 'rb') as f:
                file_id = self.fs.put(
                    f,
                    filename=filename,
                    metadata=file_metadata
                )
            
            logger.info(f"✓ Fichier uploadé vers MongoDB: {filename} (ID: {file_id})")
            
            return {
                'file_id': str(file_id),
                'filename': filename,
                'url': f"/api/recordings/download/mongo/{str(file_id)}",
                'metadata': file_metadata
            }
            
        except Exception as e:
            logger.error(f"✗ Erreur lors de l'upload MongoDB: {e}")
            raise
    
    def upload_from_memory(
        self,
        file_data: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload un fichier depuis la mémoire vers MongoDB GridFS
        
        Args:
            file_data: Données du fichier en bytes
            filename: Nom du fichier
            metadata: Métadonnées additionnelles
        
        Returns:
            Dict contenant file_id et url
        """
        try:
            # Préparer les métadonnées
            file_metadata = {
                'filename': filename,
                'upload_date': datetime.utcnow(),
                'content_type': self._get_content_type(filename),
            }
            
            if metadata:
                file_metadata.update(metadata)
            
            # Uploader le fichier
            file_id = self.fs.put(
                file_data,
                filename=filename,
                metadata=file_metadata
            )
            
            logger.info(f"✓ Fichier uploadé vers MongoDB (mémoire): {filename} (ID: {file_id})")
            
            return {
                'file_id': str(file_id),
                'filename': filename,
                'url': f"/api/recordings/download/mongo/{str(file_id)}",
                'metadata': file_metadata
            }
            
        except Exception as e:
            logger.error(f"✗ Erreur lors de l'upload MongoDB (mémoire): {e}")
            raise
    
    def download_file(self, file_id: str) -> bytes:
        """
        Télécharge un fichier depuis MongoDB GridFS
        
        Args:
            file_id: ID du fichier dans GridFS
        
        Returns:
            Contenu du fichier en bytes
        """
        try:
            from bson.objectid import ObjectId
            grid_out = self.fs.get(ObjectId(file_id))
            return grid_out.read()
        except Exception as e:
            logger.error(f"✗ Erreur lors du téléchargement MongoDB: {e}")
            raise
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les métadonnées d'un fichier
        
        Args:
            file_id: ID du fichier dans GridFS
        
        Returns:
            Métadonnées du fichier ou None
        """
        try:
            from bson.objectid import ObjectId
            grid_out = self.fs.get(ObjectId(file_id))
            return {
                'filename': grid_out.filename,
                'length': grid_out.length,
                'upload_date': grid_out.upload_date,
                'metadata': grid_out.metadata,
                'content_type': grid_out.metadata.get('content_type') if grid_out.metadata else None
            }
        except Exception as e:
            logger.error(f"✗ Erreur lors de la récupération des métadonnées: {e}")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        Supprime un fichier de MongoDB GridFS
        
        Args:
            file_id: ID du fichier à supprimer
        
        Returns:
            True si succès, False sinon
        """
        try:
            from bson.objectid import ObjectId
            self.fs.delete(ObjectId(file_id))
            logger.info(f"✓ Fichier supprimé de MongoDB: {file_id}")
            return True
        except Exception as e:
            logger.error(f"✗ Erreur lors de la suppression MongoDB: {e}")
            return False
    
    def file_exists(self, file_id: str) -> bool:
        """
        Vérifie si un fichier existe dans GridFS
        
        Args:
            file_id: ID du fichier
        
        Returns:
            True si le fichier existe, False sinon
        """
        try:
            from bson.objectid import ObjectId
            return self.fs.exists(ObjectId(file_id))
        except Exception as e:
            logger.error(f"✗ Erreur lors de la vérification d'existence: {e}")
            return False
    
    def _get_content_type(self, filename: str) -> str:
        """
        Détermine le type MIME du fichier
        
        Args:
            filename: Nom du fichier
        
        Returns:
            Type MIME
        """
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.flac': 'audio/flac',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',
            '.aac': 'audio/aac',
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def close(self):
        """Ferme la connexion MongoDB"""
        if self.client:
            self.client.close()
            logger.info("✓ Connexion MongoDB fermée")


# Instance singleton du service MongoDB
_mongodb_service = None


def get_mongodb_service() -> MongoDBService:
    """
    Retourne l'instance singleton du service MongoDB
    
    Returns:
        Instance de MongoDBService
    """
    global _mongodb_service
    if _mongodb_service is None:
        _mongodb_service = MongoDBService()
    return _mongodb_service

