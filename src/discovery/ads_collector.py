"""
Collecteur de publicités par domaine - AVEC FILTRAGE STRICT + CACHE
"""
from typing import List, Dict, Any
from src.clients.apify_client import ApifyFacebookAdsClient
from src.utils.logger import setup_logger
from src.utils.simple_cache import SimpleCache

logger = setup_logger(__name__)


class AdsCollector:
    """Collecte UNIQUEMENT les publicités liées au domaine donné avec cache"""
    
    def __init__(self, use_cache: bool = True, cache_ttl_days: int = 7):
        """
        Args:
            use_cache: Activer le cache (défaut: True)
            cache_ttl_days: Durée de validité du cache en jours (défaut: 7)
        """
        self.apify_client = ApifyFacebookAdsClient()
        self.use_cache = use_cache
        self.cache = SimpleCache(ttl_days=cache_ttl_days) if use_cache else None
    
    def collect_ads_for_domain(
        self, 
        domain: str,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Collecter UNIQUEMENT les publicités qui contiennent le domaine exact
        
        Args:
            domain: Domaine à analyser (ex: "ravino.converty.shop")
            force_refresh: Forcer le re-scraping même si en cache
            
        Returns:
            Liste des publicités FILTRÉES (uniquement celles avec le domaine)
        """
        logger.info(f"📊 Collecte des ads POUR LE DOMAINE: {domain}")
        
        # 1. Vérifier le cache d'abord (si activé)
        if self.use_cache and not force_refresh:
            cached_ads = self.cache.get(domain)
            if cached_ads is not None:
                # Cache HIT - filtrage déjà fait
                return cached_ads
        
        # 2. Cache MISS - collecter depuis Apify
        logger.info(f"🌐 Scraping Apify pour {domain}...")
        all_ads = self.apify_client.search_ads_by_domain(domain)
        logger.info(f"📥 {len(all_ads)} ads brutes récupérées")
        
        # 3. Filtrer STRICTEMENT
        filtered_ads = self._filter_ads_strictly_by_domain(all_ads, domain)
        logger.info(f"✅ {len(filtered_ads)} ads FILTRÉES pour {domain}")
        
        # 4. Sauvegarder dans le cache
        if self.use_cache:
            self.cache.set(domain, filtered_ads)
        
        return filtered_ads
    
    def _filter_ads_strictly_by_domain(
        self, 
        ads: List[Dict[str, Any]], 
        target_domain: str
    ) -> List[Dict[str, Any]]:
        """
        Filtrer STRICTEMENT les ads pour garder uniquement celles avec le domaine exact
        """
        filtered_ads = []
        
        for ad in ads:
            if self._ad_contains_domain(ad, target_domain):
                filtered_ads.append(ad)
                logger.debug(f"✓ Ad {ad.get('ad_archive_id')} contient {target_domain}")
            else:
                logger.debug(f"✗ Ad {ad.get('ad_archive_id')} ignorée (pas de domaine {target_domain})")
        
        return filtered_ads
    
    def _ad_contains_domain(self, ad: Dict[str, Any], target_domain: str) -> bool:
        """
        Vérifier si l'ad contient le domaine exact dans ses URLs
        """
        snapshot = ad.get('snapshot', {})
        
        # Sécurité : si snapshot est None
        if not snapshot:
            return False
        
        # 1. Vérifier le lien principal
        link_url = snapshot.get('link_url') or ''  # Protection contre None
        if target_domain in link_url:
            return True
        
        # 2. Vérifier dans les cards (carousel)
        cards = snapshot.get('cards') or []  # Protection contre None
        for card in cards:
            if not card:  # Protection contre None
                continue
            card_link = card.get('link_url') or ''
            if target_domain in card_link:
                return True
        
        # 3. Vérifier la caption
        caption = snapshot.get('caption') or ''  # Protection contre None
        if target_domain in caption:
            return True
        
        return False