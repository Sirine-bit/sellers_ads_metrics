"""
DataLoader - Charge les données depuis MongoDB pour le dashboard
"""
from typing import Dict, List, Any
from datetime import datetime
from src.database.mongo_client import MongoDBClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DataLoader:
    """Charge toutes les données nécessaires au dashboard depuis MongoDB"""
    
    def __init__(self):
        """Initialiser la connexion MongoDB"""
        self.mongo_client = MongoDBClient()
        self.db = self.mongo_client.db
        logger.info("DataLoader initialisé avec connexion MongoDB")
    
    def get_all_stores(self) -> List[Dict[str, Any]]:
        """
        Récupérer TOUS les clients de la collection stores
        
        Returns:
            Liste de tous les clients (21,764 total)
        """
        stores = list(self.db.stores.find())
        logger.info(f"Chargé {len(stores)} clients depuis stores")
        return stores
    
    def get_mappings(self, status_filter: str = None) -> List[Dict[str, Any]]:
        """
        Récupérer les mappings Phase 1 (type='mapping')
        
        Args:
            status_filter: Filtrer par status ('active', 'inactive', None=tous)
        
        Returns:
            Liste des mappings Phase 1
        """
        query = {'type': 'mapping'}
        if status_filter:
            query['status'] = status_filter
        
        mappings = list(self.db.ads_metrics.find(query))
        logger.info(f"Chargé {len(mappings)} mappings (filtre: {status_filter or 'tous'})")
        return mappings
    
    def get_reports(self, status_filter: str = None) -> List[Dict[str, Any]]:
        """
        Récupérer les rapports Phase 2 (type='report')
        
        Args:
            status_filter: Filtrer par status
        
        Returns:
            Liste des rapports de classification Phase 2
        """
        query = {'type': 'report'}
        if status_filter:
            query['status'] = status_filter
        
        reports = list(self.db.ads_metrics.find(query))
        logger.info(f"Chargé {len(reports)} rapports Phase 2")
        return reports
    
    def get_client_detail(self, client_id: str) -> Dict[str, Any]:
        """
        Récupérer TOUTES les données d'un client spécifique
        
        Args:
            client_id: ID du client
        
        Returns:
            {
                'store': {...},           # Info store
                'mapping': {...},         # Mapping Phase 1
                'report': {...}           # Rapport Phase 2 (si existe)
            }
        """
        # Store
        store = self.db.stores.find_one({'slug': client_id})
        
        # Mapping Phase 1
        mapping = self.db.ads_metrics.find_one({
            'client_id': client_id,
            'type': 'mapping'
        })
        
        # Report Phase 2
        report = self.db.ads_metrics.find_one({
            'client_id': client_id,
            'type': 'report'
        })
        
        return {
            'store': store,
            'mapping': mapping,
            'report': report
        }
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Charger TOUTES les données en une seule fois (pour cache Streamlit)
        
        Returns:
            {
                'stores': [...],           # Tous les clients
                'mappings': [...],         # Mappings Phase 1
                'mappings_active': [...],  # Mappings actifs uniquement
                'mappings_inactive': [...],# Mappings inactifs
                'reports': [...],          # Rapports Phase 2
                'loaded_at': datetime      # Timestamp chargement
            }
        """
        logger.info("Chargement complet des données...")
        
        # Charger tout
        stores = self.get_all_stores()
        all_mappings = self.get_mappings()
        mappings_active = self.get_mappings(status_filter='active')
        mappings_inactive = self.get_mappings(status_filter='inactive')
        reports = self.get_reports()
        
        data = {
            'stores': stores,
            'mappings': all_mappings,
            'mappings_active': mappings_active,
            'mappings_inactive': mappings_inactive,
            'reports': reports,
            'loaded_at': datetime.now()
        }
        
        logger.info(f"Chargement terminé: {len(stores)} stores, "
                   f"{len(all_mappings)} mappings, {len(reports)} reports")
        
        return data
    
    def close(self):
        """Fermer la connexion MongoDB"""
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("Connexion MongoDB fermée")
