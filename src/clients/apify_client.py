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
        country: str = None,
        max_items: int = None,  # ✨ NOUVEAU: limiter le nombre d'items
        memory_mb: int = 512,   # ✨ NOUVEAU: optimiser la mémoire
        timeout_secs: int = 300  # ✨ NOUVEAU: timeout pour éviter les runs trop longs
    ) -> List[Dict[str, Any]]:
        """
        Chercher TOUTES les publicités pour un domaine avec optimisation des coûts
        
        Args:
            domain: Domaine à rechercher (ex: ravino.converty.shop)
            country: Code pays (ex: TN)
            max_items: Nombre maximum d'items (None = illimité, optimisation: 100-500)
            memory_mb: Mémoire allouée en MB (défaut: 512, minimum recommandé)
            timeout_secs: Timeout en secondes (défaut: 300 = 5 min)
            
        Returns:
            Liste de TOUTES les publicités trouvées
        """
        country = country or settings.DEFAULT_COUNTRY
        
        # Construire l'URL complète de Meta Ad Library
        meta_url = self._build_meta_ad_library_url(domain, country)
        
        logger.info(f"🔍 Recherche pour: {domain}")
        logger.info(f"📍 URL: {meta_url}")
        
        try:
            # ✅ OPTIMISATION: Limiter le nombre d'items si spécifié
            # 200 par défaut = optimal pour la majorité des clients (économie 60% vs 9999)
            count = max_items if max_items else 200
            
            run_input = {
                "urls": [
                    {"url": meta_url}
                ],
                "count": count,  # ✅ Limiter le scraping
                "period": "",
                "scrapePageAds.activeStatus": "all",
                "scrapePageAds.countryCode": "ALL",
                "proxyConfiguration": {
                    "useApifyProxy": True
                }
            }
            
            logger.debug(f"Input: {run_input}")
            logger.debug(f"Options: memory={memory_mb}MB, timeout={timeout_secs}s, max_items={count}")
            logger.info(f"🚀 Lancement de l'Actor (max={count} ads, {memory_mb}MB, {timeout_secs}s timeout)...")
            
            # ✅ CORRECTION: Les paramètres memory_mbytes et timeout_secs doivent être passés dans build
            # Retry automatique intégré (3 tentatives)
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    run = self.client.actor(self.actor_id).call(
                        run_input=run_input,
                        build="latest",
                        memory_mbytes=memory_mb,
                        timeout_secs=timeout_secs
                    )
                    break  # Succès, sortir de la boucle
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(f"⚠️ Tentative {attempt + 1}/{max_retries} échouée: {e}. Retry dans {wait_time}s...")
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ Échec après {max_retries} tentatives")
                        raise last_error
            
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
        country: str = None,
        max_items: int = None,
        memory_mb: int = 512,
        timeout_secs: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Récupérer les publicités d'une page Facebook
        (Utilisé en Phase 2)
        
        Args:
            page_id: ID de la page Facebook
            country: Code pays
            max_items: Limite d'ads (défaut: 500 pour Phase 2)
            memory_mb: Mémoire allouée
            timeout_secs: Timeout
            
        Returns:
            Liste des publicités de cette page
        """
        country = country or settings.DEFAULT_COUNTRY
        count = max_items if max_items else 500  # ✅ Optimisé pour Phase 2
        
        logger.info(f"🔍 Récupération des ads de la page: {page_id} (max={count})")
        
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
                "count": count,  # ✅ Optimisé
                "period": "",
                "scrapePageAds.activeStatus": "all",
                "scrapePageAds.countryCode": "ALL",
                "proxyConfiguration": {"useApifyProxy": True}
            }
            
            logger.debug(f"URL: {meta_url}")
            logger.info(f"🚀 Lancement de l'Actor (max={count} ads, {memory_mb}MB)...")
            
            # Retry automatique
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    run = self.client.actor(self.actor_id).call(
                        run_input=run_input,
                        memory_mbytes=memory_mb,
                        timeout_secs=timeout_secs
                    )
                    break
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"⚠️ Retry {attempt + 1}/{max_retries}: {e}. Attente {wait_time}s...")
                        import time
                        time.sleep(wait_time)
                    else:
                        raise last_error
            
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
        
    