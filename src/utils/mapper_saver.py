"""
Sauvegarde des mappings dans MongoDB via MongoDBClient unifié
"""
from typing import Dict
from src.database.mongo_client import MongoDBClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MongoMapperSaver:
    """
    Wrapper simplifié pour sauvegarder les mappings dans MongoDB
    Utilise le MongoDBClient unifié
    """
    
    def __init__(self):
        self.mongo_client = MongoDBClient()
        logger.info("✓ MongoMapperSaver initialisé")
    
    def save_mapping(self, mapping: Dict, processing_metadata: Dict = None) -> bool:
        """
        Sauvegarder un mapping dans MongoDB
        
        Args:
            mapping: Résultat du mapping (format SiteMapper)
            processing_metadata: Métadonnées du traitement
        
        Returns:
            True si succès, False sinon
        """
        return self.mongo_client.save_mapping(mapping, processing_metadata)
    
    def mark_as_failed(self, client_id: str, error: str, 
                      processing_metadata: Dict = None) -> bool:
        """
        Marquer un client comme échoué
        
        Args:
            client_id: ID du client
            error: Message d'erreur
            processing_metadata: Métadonnées du traitement
        """
        return self.mongo_client.mark_mapping_as_failed(
            client_id, 
            error, 
            processing_metadata
        )
    
    def get_mapping(self, client_id: str) -> Dict:
        """
        Récupérer le mapping d'un client
        
        Args:
            client_id: ID du client
        
        Returns:
            Document MongoDB ou None
        """
        return self.mongo_client.get_mapping(client_id)
    
    def get_all_mappings(self, status: str = None) -> list:
        """
        Récupérer tous les mappings
        
        Args:
            status: Filtrer par status ('completed', 'failed', None pour tous)
        
        Returns:
            Liste des documents
        """
        return self.mongo_client.get_all_mappings(status)
    
    def get_statistics(self) -> Dict:
        """Obtenir des statistiques sur les mappings"""
        return self.mongo_client.get_mapping_statistics()
    
    def delete_mapping(self, client_id: str) -> bool:
        """Supprimer le mapping d'un client"""
        return self.mongo_client.delete_mapping(client_id)
    
    def is_already_processed(self, client_id: str) -> bool:
        """
        Vérifier si un client a déjà été traité avec succès
        
        Args:
            client_id: ID du client
        
        Returns:
            True si déjà traité avec succès
        """
        return self.mongo_client.is_mapping_completed(client_id)