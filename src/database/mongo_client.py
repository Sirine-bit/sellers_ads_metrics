"""
Client MongoDB unifié pour toutes les opérations
Gère: stores, ads_metrics (Phase 1 mapping + Phase 2 analysis)
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
    """Client MongoDB unifié pour Converty"""
    
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
        """Créer tous les indexes nécessaires"""
        try:
            collection = self.db['ads_metrics']
            
            # Index pour Phase 1 (mapping)
            collection.create_index('client_id', unique=False, name='idx_client_id')
            collection.create_index('processing_status', name='idx_status')
            collection.create_index('timestamp', name='idx_timestamp')
            collection.create_index(
                [('client_id', ASCENDING), ('type', ASCENDING)],
                name='idx_client_type'
            )
            
            # Index pour Phase 2 (analysis/report)
            collection.create_index([
                ('client_slug', ASCENDING),
                ('analyzed_at', DESCENDING)
            ], name='idx_client_analyzed')
            
            collection.create_index('store_id', name='idx_store')
            collection.create_index('domain', name='idx_domain')
            collection.create_index(
                [('analyzed_at', DESCENDING)], 
                name='idx_analyzed_desc'
            )
            
            # Index composite pour type de document
            collection.create_index(
                [('type', ASCENDING), ('timestamp', DESCENDING)],
                name='idx_type_timestamp'
            )
            
            logger.info("✅ Indexes MongoDB créés/vérifiés")
        except Exception as e:
            logger.warning(f"⚠️ Erreur création indexes: {e}")
    
    # ========================================================================
    # PHASE 1: DISCOVERY & MAPPING
    # ========================================================================
    
    def save_mapping(self, mapping: Dict, processing_metadata: Dict = None) -> bool:
        """
        Sauvegarder un mapping de Phase 1 dans ads_metrics
        
        Args:
            mapping: Résultat du mapping (format SiteMapper)
            processing_metadata: Métadonnées du traitement
        
        Returns:
            True si succès, False sinon
        """
        try:
            client_id = mapping['client_id']
            
            # Calculer le total d'ads pour déterminer le statut
            total_ads = sum(m['total_ads'] for m in mapping.get('mappings', []))
            is_active = mapping.get('is_active', total_ads >= 5)
            
            # Préparer le document
            document = {
                'client_id': client_id,
                'type': 'mapping',  # Type Phase 1
                'timestamp': datetime.now(),
                'processing_status': 'completed',
                
                # 🎯 STATUT ACTIVITÉ (simplifié)
                'status': 'active' if is_active else 'inactive',
                'is_active': is_active,
                'phase2_recommendation': 'PROCESS' if is_active else 'SKIP',
                
                # Statistiques globales
                'stats': {
                    'total_sites': len(mapping.get('mappings', [])),
                    'total_ads': total_ads,
                    'total_fb_pages': sum(len(m['fb_pages']) for m in mapping.get('mappings', [])),
                    'sites_with_ads': sum(1 for m in mapping.get('mappings', []) if m['total_ads'] > 0),
                    'sites_with_pages': sum(1 for m in mapping.get('mappings', []) if m['fb_pages'])
                },
                
                # Détails par site
                'sites_mapping': [],
                
                # Métadonnées de traitement
                'processing_metadata': processing_metadata or {}
            }
            
            # Transformer les mappings
            for site_mapping in mapping.get('mappings', []):
                site_data = {
                    'site': site_mapping['site'],
                    'total_ads': site_mapping['total_ads'],
                    'discovery_timestamp': site_mapping.get('timestamp'),
                    
                    # Pages Facebook
                    'fb_pages': [
                        {
                            'page_id': page['page_id'],
                            'page_name': page['page_name'],
                            'page_url': page['page_url'],
                            'ads_count': page['ads_count'],
                            'confidence': page['confidence'],
                            'sample_ads': page.get('sample_ads', [])
                        }
                        for page in site_mapping.get('fb_pages', [])
                    ],
                    
                    # Métadonnées
                    'metadata': {
                        'has_ads': site_mapping['total_ads'] > 0,
                        'has_fb_pages': len(site_mapping.get('fb_pages', [])) > 0,
                        'best_match_confidence': max(
                            [p['confidence'] for p in site_mapping.get('fb_pages', [])],
                            default=0
                        )
                    }
                }
                
                document['sites_mapping'].append(site_data)
            
            # Upsert (mise à jour ou insertion)
            result = self.db.ads_metrics.update_one(
                {'client_id': client_id, 'type': 'mapping'},
                {'$set': document},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"✅ Nouveau mapping créé pour {client_id}")
            else:
                logger.info(f"✅ Mapping mis à jour pour {client_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde mapping pour {mapping.get('client_id')}: {e}")
            return False
    
    def mark_mapping_as_failed(self, client_id: str, error: str, 
                               processing_metadata: Dict = None) -> bool:
        """Marquer un mapping comme échoué (enregistré comme inactive)"""
        try:
            document = {
                'client_id': client_id,
                'type': 'mapping',
                'timestamp': datetime.now(),
                'processing_status': 'failed',
                # 🎯 Simplifié : juste inactive, pas de détails d'erreur
                'status': 'inactive',
                'is_active': False,
                'phase2_recommendation': 'SKIP',
                'processing_metadata': processing_metadata or {},
                'stats': {
                    'total_sites': 0,
                    'total_ads': 0,
                    'total_fb_pages': 0
                },
                'sites_mapping': []
            }
            
            result = self.db.ads_metrics.update_one(
                {'client_id': client_id, 'type': 'mapping'},
                {'$set': document},
                upsert=True
            )
            
            logger.info(f"❌ Échec mapping enregistré pour {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur enregistrement échec pour {client_id}: {e}")
            return False
    
    def get_mapping(self, client_id: str) -> Optional[Dict]:
        """Récupérer le mapping d'un client"""
        try:
            return self.db.ads_metrics.find_one({
                'client_id': client_id,
                'type': 'mapping'
            })
        except Exception as e:
            logger.error(f"❌ Erreur récupération mapping pour {client_id}: {e}")
            return None
    
    def is_mapping_completed(self, client_id: str) -> bool:
        """Vérifier si le mapping est complété avec succès"""
        try:
            doc = self.db.ads_metrics.find_one({
                'client_id': client_id,
                'type': 'mapping',
                'processing_status': 'completed'
            })
            return doc is not None
        except Exception as e:
            logger.error(f"❌ Erreur vérification mapping pour {client_id}: {e}")
            return False
    
    # ========================================================================
    # PHASE 2: ANALYSIS & REPORTING
    # ========================================================================
    
    def save_ad_metrics(
        self, 
        client_slug: str,
        domain: str,
        report: Dict[str, Any],
        store_id: ObjectId = None
    ) -> Optional[str]:
        """
        Sauvegarder les métriques publicitaires (Phase 2)
        
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
                'client_id': client_slug,  # Alias pour compatibilité
                'store_id': store_id,
                'domain': domain,
                'type': 'report',  # Type Phase 2
                'analyzed_at': datetime.fromisoformat(report['analyzed_at']),
                'timestamp': datetime.utcnow(),
                
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
                
                # Métadonnées
                'version': '2.0',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Insérer dans MongoDB
            result = self.db.ads_metrics.insert_one(metrics_doc)
            
            logger.info(f"✅ Métriques Phase 2 sauvegardées pour {client_slug} (ID: {result.inserted_id})")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde métriques Phase 2 {client_slug}: {e}")
            return None
    
    def save_ads_metrics(self, store_slug: str, metrics_data: Dict[str, Any]):
        """
        Sauvegarder les métriques publicitaires (format simplifié)
        Alias pour compatibilité avec l'ancien code
        
        Args:
            store_slug: Identifiant du magasin
            metrics_data: Données des métriques
        """
        try:
            mongo_doc = {
                'store_slug': store_slug,
                'client_id': store_slug,
                'type': 'report',
                'timestamp': datetime.utcnow(),
                'total_ads': metrics_data.get('total_ads', 0),
                'stats': metrics_data.get('stats', {}),
                'pages': metrics_data.get('pages', []),
                'ads_details': metrics_data.get('ads_details', []),
                'summary': {
                    'total_analyzed': metrics_data.get('total_ads', 0),
                    'converty_ads': sum(1 for ad in metrics_data.get('ads_details', []) 
                                       if ad.get('classification') == 'CONVERTY'),
                    'competitor_ads': sum(1 for ad in metrics_data.get('ads_details', []) 
                                         if ad.get('classification') == 'CONCURRENT'),
                    'unknown_ads': sum(1 for ad in metrics_data.get('ads_details', []) 
                                      if ad.get('classification') == 'UNKNOWN')
                }
            }
            
            result = self.db.ads_metrics.insert_one(mongo_doc)
            
            logger.info(f"✅ Métriques sauvegardées pour {store_slug} (ID: {result.inserted_id})")
            return result.inserted_id
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde métriques pour {store_slug}: {e}")
            raise
    
    # ========================================================================
    # STORES - Gestion des magasins
    # ========================================================================
    
    def get_all_stores(self) -> List[Dict[str, Any]]:
        """Récupérer tous les magasins"""
        try:
            stores = list(self.db.stores.find({}))
            logger.info(f"✅ {len(stores)} magasins récupérés")
            return stores
        except Exception as e:
            logger.error(f"❌ Erreur récupération magasins: {e}")
            raise
    
    def get_store_by_slug(self, slug: str) -> Optional[Dict]:
        """Récupérer un store par son slug"""
        try:
            store = self.db.stores.find_one({'slug': slug})
            return store
        except Exception as e:
            logger.error(f"❌ Erreur récupération store {slug}: {e}")
            return None
    
    # ========================================================================
    # REQUÊTES & STATISTIQUES
    # ========================================================================
    
    def get_latest_metrics(self, client_slug: str) -> Optional[Dict]:
        """Récupérer les dernières métriques (Phase 2)"""
        try:
            metrics = self.db.ads_metrics.find_one(
                {'client_slug': client_slug, 'type': 'report'},
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
        """Récupérer l'historique des métriques"""
        try:
            cursor = self.db.ads_metrics.find(
                {'client_slug': client_slug, 'type': 'report'}
            ).sort('analyzed_at', DESCENDING).limit(limit)
            
            return list(cursor)
        except Exception as e:
            logger.error(f"❌ Erreur historique {client_slug}: {e}")
            return []
    
    def get_all_mappings(self, status: str = None) -> List[Dict]:
        """Récupérer tous les mappings (Phase 1)"""
        try:
            query = {'type': 'mapping'}
            if status:
                query['processing_status'] = status
            
            return list(self.db.ads_metrics.find(query).sort('timestamp', -1))
        except Exception as e:
            logger.error(f"❌ Erreur récupération mappings: {e}")
            return []
    
    def get_mapping_statistics(self) -> Dict:
        """Obtenir des statistiques sur les mappings"""
        try:
            pipeline = [
                {'$match': {'type': 'mapping'}},
                {
                    '$group': {
                        '_id': '$processing_status',
                        'count': {'$sum': 1},
                        'total_ads': {'$sum': '$stats.total_ads'},
                        'total_fb_pages': {'$sum': '$stats.total_fb_pages'}
                    }
                }
            ]
            
            results = list(self.db.ads_metrics.aggregate(pipeline))
            
            stats = {
                'total_clients': self.db.ads_metrics.count_documents({'type': 'mapping'}),
                'by_status': {r['_id']: r for r in results},
                'last_update': None
            }
            
            # Dernier timestamp
            last_doc = self.db.ads_metrics.find_one(
                {'type': 'mapping'},
                sort=[('timestamp', -1)]
            )
            if last_doc:
                stats['last_update'] = last_doc.get('timestamp')
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul statistiques: {e}")
            return {}
    
    def delete_mapping(self, client_id: str) -> bool:
        """Supprimer le mapping d'un client"""
        try:
            result = self.db.ads_metrics.delete_one({
                'client_id': client_id,
                'type': 'mapping'
            })
            if result.deleted_count > 0:
                logger.info(f"🗑️ Mapping supprimé pour {client_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Erreur suppression mapping pour {client_id}: {e}")
            return False
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def close(self):
        """Fermer la connexion MongoDB"""
        if self.client:
            self.client.close()
            logger.info("🔌 Connexion MongoDB fermée")