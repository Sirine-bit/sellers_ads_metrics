"""
Client Apify pour la collecte des publicités Facebook
Actor: curious_coder/facebook-ads-library-scraper
"""
from typing import List, Dict, Any
from apify_client import ApifyClient
from config.settings import settings
from src.utils.logger import setup_logger
from urllib.parse import quote

logger = setup_logger(__name__)


class ApifyFacebookAdsClient:
    """Client pour interagir avec Apify et collecter les ads Facebook"""
    
    def __init__(self):
        """Initialiser le client Apify"""
        self.client = ApifyClient(settings.APIFY_API_TOKEN)
        self.actor_id = settings.APIFY_ACTOR_ID
        
        logger.info(f"✓ Client Apify initialisé")
        logger.info(f"  Actor: {self.actor_id}")
    
    def search_ads_by_domain(
        self, 
        domain: str, 
        country: str = None
    ) -> List[Dict[str, Any]]:
        """
        Chercher TOUTES les publicités pour un domaine
        
        Args:
            domain: Domaine à rechercher (ex: ravino.converty.shop)
            country: Code pays (ex: TN)
            
        Returns:
            Liste de TOUTES les publicités trouvées
        """
        country = country or settings.DEFAULT_COUNTRY
        
        # Construire l'URL complète de Meta Ad Library
        meta_url = self._build_meta_ad_library_url(domain, country)
        
        logger.info(f"🔍 Recherche pour: {domain}")
        logger.info(f"📍 URL: {meta_url}")
        
        try:
            # ✅ CORRECTION : Format correct pour l'Actor
            run_input = {
                "urls": [
                    {"url": meta_url}  # ✅ Liste de dictionnaires avec clé "url"
                ],
                "count": 9999,  # ✅ Utiliser "count" au lieu de "maxItems"
                "period": "",  # ✅ Période vide pour toutes les dates
                "scrapePageAds.activeStatus": "all",  # ✅ Tous les statuts
                "scrapePageAds.countryCode": "ALL",   # ✅ Tous les pays
                "proxyConfiguration": {
                    "useApifyProxy": True
                }
            }
            
            logger.debug(f"Input: {run_input}")
            logger.info("🚀 Lancement de l'Actor...")
            
            # Lancer l'Actor
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            
            # Récupérer les résultats
            ads = []
            dataset_id = run.get("defaultDatasetId")
            
            if not dataset_id:
                logger.warning("⚠️  Aucun dataset retourné")
                return []
            
            logger.info(f"📊 Récupération des données du dataset {dataset_id}...")
            
            # Parcourir TOUS les items
            item_count = 0
            for item in self.client.dataset(dataset_id).iterate_items():
                ads.append(item)
                item_count += 1
                
                if item_count % 50 == 0:
                    logger.info(f"  → {item_count} publicités récupérées...")
            
            logger.info(f"✅ TOTAL: {len(ads)} publicités récupérées pour '{domain}'")
            
            # Debug: afficher la structure
            if ads and len(ads) > 0:
                logger.debug(f"Champs disponibles: {list(ads[0].keys())[:15]}")
            elif len(ads) == 0:
                logger.warning(f"⚠️  Aucune publicité trouvée pour '{domain}'")
            
            return ads
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la collecte: {str(e)}")
            raise


    def get_all_ads_by_page_id(
        self, 
        page_id: str,
        country: str = None
    ) -> List[Dict[str, Any]]:
        """
        Récupérer TOUTES les publicités d'une page Facebook
        (Utilisé en Phase 2)
        
        Args:
            page_id: ID de la page Facebook
            country: Code pays
            
        Returns:
            Liste de TOUTES les publicités de cette page
        """
        country = country or settings.DEFAULT_COUNTRY
        
        logger.info(f"🔍 Récupération de TOUTES les ads de la page: {page_id}")
        
        try:
            # URL pour rechercher par page ID
            meta_url = (
                f"https://www.facebook.com/ads/library/"
                f"?active_status=all"
                f"&ad_type=all"
                f"&country={country}"
                f"&view_all_page_id={page_id}"
                f"&search_type=page"
                f"&media_type=all"
            )
            
            run_input = {
                "urls": [{"url": meta_url}],
                "count": 9999,
                "period": "",
                "scrapePageAds.activeStatus": "all",
                "scrapePageAds.countryCode": "ALL",
                "proxyConfiguration": {"useApifyProxy": True}
            }
            
            logger.debug(f"URL: {meta_url}")
            logger.info("🚀 Lancement de l'Actor...")
            
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            
            ads = []
            dataset_id = run.get("defaultDatasetId")
            
            if not dataset_id:
                logger.warning("⚠️  Aucun dataset retourné")
                return []
            
            item_count = 0
            for item in self.client.dataset(dataset_id).iterate_items():
                # Filtrer pour ne garder que les ads de cette page
                if str(item.get('page_id')) == str(page_id):
                    ads.append(item)
                    item_count += 1
                    
                    if item_count % 50 == 0:
                        logger.info(f"  → {item_count} publicités...")
            
            logger.info(f"✅ TOTAL: {len(ads)} publicités de la page")
            
            return ads
            
        except Exception as e:
            logger.error(f"❌ Erreur: {str(e)}")
            raise
        
    
    def _build_meta_ad_library_url(
        self, 
        domain: str, 
        country: str
    ) -> str:
        """
        Construire l'URL complète de Meta Ad Library
        
        Args:
            domain: Domaine à rechercher
            country: Code pays
            
        Returns:
            URL complète
        """
        encoded_domain = quote(domain)
        
        url = (
            f"https://www.facebook.com/ads/library/"
            f"?active_status=all"  # ✅ "all" au lieu de "active" pour toutes les publicités
            f"&ad_type=all"
            f"&country={country}"
            f"&is_targeted_country=false"
            f"&media_type=all"
            f"&q={encoded_domain}"
            f"&search_type=keyword_unordered"
        )
        
        return url
    
    def get_all_active_ads_by_domain(
        self, 
        domain: str, 
        country: str = None
    ) -> List[Dict[str, Any]]:
        """
        Chercher UNIQUEMENT les publicités ACTIVES
        
        Args:
            domain: Domaine à rechercher
            country: Code pays
            
        Returns:
            Liste des ads actives
        """
        return self.search_ads_by_domain(domain, country)
    
    def test_connection(self) -> bool:
        """Tester la connexion à Apify"""
        try:
            logger.info("🔧 Test de connexion à Apify...")
            user = self.client.user().get()
            logger.info(f"✅ Connecté en tant que: {user.get('username', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"❌ Échec de connexion: {str(e)}")
            return False
        
    