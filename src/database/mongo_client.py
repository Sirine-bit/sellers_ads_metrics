"""
Client MongoDB pour stocker les métriques publicitaires
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
import os
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MongoDBClient:
    """Client MongoDB pour les métriques Facebook Ads"""
    
    def __init__(self, connection_string: str = None):
        """
        Initialiser la connexion MongoDB
        
        Args:
            connection_string: URI MongoDB (défaut: 127.0.0.1:27017)
        """
        self.connection_string = connection_string or os.getenv(
            'MONGODB_URI', 
            'mongodb://127.0.0.1:27017/?directConnection=true'
        )
        self.client = None
        self.db = None
        self._connect()
        
    def get_all_stores(self) -> List[Dict[str, Any]]:
        """
        Récupérer tous les magasins depuis la collection stores
        
        Returns:
            Liste des magasins avec leurs informations
        """
        try:
            stores = list(self.db.stores.find({}))
            logger.info(f"✅ {len(stores)} magasins récupérés depuis MongoDB")
            return stores
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des magasins: {e}")
            raise
            
    def save_ads_metrics(self, store_slug: str, metrics_data: Dict[str, Any]):
        """
        Sauvegarder les métriques publicitaires dans la collection ads_metrics
        
        Args:
            store_slug: Identifiant du magasin
            metrics_data: Données des métriques à sauvegarder
        """
        try:
            # Structurer les données pour MongoDB
            mongo_doc = {
                'store_slug': store_slug,
                'timestamp': datetime.utcnow(),
                'type': 'report',
                'total_ads': metrics_data.get('total_ads', 0),
                'stats': metrics_data.get('stats', {}),
                'pages': metrics_data.get('pages', []),
                # Garder les détails de chaque annonce
                'ads_details': metrics_data.get('ads_details', []),
                # Ajouter les statistiques agrégées
                'summary': {
                    'total_analyzed': metrics_data.get('total_ads', 0),
                    'converty_ads': sum(1 for ad in metrics_data.get('ads_details', []) if ad.get('classification') == 'CONVERTY'),
                    'competitor_ads': sum(1 for ad in metrics_data.get('ads_details', []) if ad.get('classification') == 'CONCURRENT'),
                    'unknown_ads': sum(1 for ad in metrics_data.get('ads_details', []) if ad.get('classification') == 'UNKNOWN')
                }
            }
            
            # Insérer dans la collection
            result = self.db.ads_metrics.insert_one(mongo_doc)
            
            logger.info(f"✅ Métriques sauvegardées pour {store_slug} (ID: {result.inserted_id})")
            return result.inserted_id
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde des métriques pour {store_slug}: {e}")
            raise
    
    def _connect(self):
        """Établir la connexion à MongoDB"""
        try:
            self.client = MongoClient(self.connection_string)
            # Test de connexion
            self.client.admin.command('ping')
            
            # Sélectionner la base de données
            self.db = self.client['converty']
            
            logger.info("✅ Connecté à MongoDB (converty)")
            
            # Créer les indexes
            self._create_indexes()
            
        except ConnectionFailure as e:
            logger.error(f"❌ Échec de connexion MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Créer les indexes pour optimiser les requêtes"""
        collection = self.db['ads_metrics']
        
        # Index sur client_slug + analyzed_at (pour historique)
        collection.create_index([
            ('client_slug', ASCENDING),
            ('analyzed_at', DESCENDING)
        ], name='idx_client_analyzed')
        
        # Index sur store_id
        collection.create_index('store_id', name='idx_store')
        
        # Index sur domain
        collection.create_index('domain', name='idx_domain')
        
        # Index sur analyzed_at (pour retrouver les dernières analyses)
        collection.create_index(
            [('analyzed_at', DESCENDING)], 
            name='idx_analyzed_desc'
        )
        
        logger.info("✅ Indexes MongoDB créés")
    
    def get_store_by_slug(self, slug: str) -> Optional[Dict]:
        """
        Récupérer un store par son slug
        
        Args:
            slug: Slug du client
            
        Returns:
            Document store ou None
        """
        try:
            store = self.db['stores'].find_one({'slug': slug})
            return store
        except Exception as e:
            logger.error(f"❌ Erreur récupération store {slug}: {e}")
            return None
    
    def save_ad_metrics(
        self, 
        client_slug: str,
        domain: str,
        report: Dict[str, Any],
        store_id: ObjectId = None
    ) -> Optional[str]:
        """
        Sauvegarder les métriques publicitaires
        
        Args:
            client_slug: Slug du client
            domain: Domaine principal
            report: Rapport de Phase 2
            store_id: ID du store (optionnel)
            
        Returns:
            ID du document créé ou None
        """
        try:
            # Récupérer store_id si non fourni
            if not store_id:
                store = self.get_store_by_slug(client_slug)
                if store:
                    store_id = store['_id']
            
            # Préparer le document
            metrics_doc = {
                'client_slug': client_slug,
                'store_id': store_id,
                'domain': domain,
                'analyzed_at': datetime.fromisoformat(report['analyzed_at']),
                
                # Métriques globales
                'metrics': report['global_stats'],
                
                # Pages Facebook
                'facebook_pages': [
                    {
                        'page_id': page['page_id'],
                        'page_name': page['page_name'],
                        'total_ads': page['total_ads'],
                        'converty_ads': page['converty_ads'],
                        'concurrent_ads': page['concurrent_ads'],
                        'converty_ratio': page['converty_ratio']
                    }
                    for page in report['page_details']
                ],
                
                # Concurrents
                'competitors': report['top_competitors'],
                
                # Détails des pubs (optionnel - peut être lourd)
                # Décommenter si vous voulez stocker tous les détails
                # 'ads_details': self._extract_ads_details(report),
                
                # Métadonnées
                'version': '2.0',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            # Marquer le type de document (Phase 2 = report)
            metrics_doc['type'] = 'report'
            
            # Insérer dans MongoDB
            result = self.db['ads_metrics'].insert_one(metrics_doc)
            
            logger.info(f"✅ Métriques sauvegardées pour {client_slug} (ID: {result.inserted_id})")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde métriques {client_slug}: {e}")
            return None
    
    def _extract_ads_details(self, report: Dict[str, Any]) -> List[Dict]:
        """Extraire les détails simplifiés des publicités"""
        ads_details = []
        
        for page in report['page_details']:
            for ad in page['classified_ads']:
                ads_details.append({
                    'ad_id': ad['ad_id'],
                    'classification': ad['classification'],
                    'platform': ad.get('competitor_platform'),
                    'destination_url': ad['destination_url'],
                    'confidence': ad['confidence']
                })
        
        return ads_details
    
    def get_latest_metrics(self, client_slug: str) -> Optional[Dict]:
        """
        Récupérer les dernières métriques d'un client
        
        Args:
            client_slug: Slug du client
            
        Returns:
            Document de métriques ou None
        """
        try:
            metrics = self.db['ads_metrics'].find_one(
                {'client_slug': client_slug},
                sort=[('analyzed_at', DESCENDING)]
            )
            return metrics
        except Exception as e:
            logger.error(f"❌ Erreur récupération métriques {client_slug}: {e}")
            return None
    
    def get_metrics_history(
        self, 
        client_slug: str, 
        limit: int = 10
    ) -> List[Dict]:
        """
        Récupérer l'historique des métriques
        
        Args:
            client_slug: Slug du client
            limit: Nombre de résultats
            
        Returns:
            Liste des métriques historiques
        """
        try:
            cursor = self.db['ads_metrics'].find(
                {'client_slug': client_slug}
            ).sort('analyzed_at', DESCENDING).limit(limit)
            
            return list(cursor)
        except Exception as e:
            logger.error(f"❌ Erreur historique {client_slug}: {e}")
            return []
    
    def close(self):
        """Fermer la connexion MongoDB"""
        if self.client:
            self.client.close()
            logger.info("🔌 Connexion MongoDB fermée")