"""
Collecteur de publicités par domaine - AVEC FILTRAGE STRICT
"""
from typing import List, Dict, Any
from src.clients.apify_client import ApifyFacebookAdsClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AdsCollector:
    """Collecte UNIQUEMENT les publicités liées au domaine donné"""
    
    def __init__(self):
        self.apify_client = ApifyFacebookAdsClient()
    
    def collect_ads_for_domain(
        self, 
        domain: str
    ) -> List[Dict[str, Any]]:
        """
        Collecter UNIQUEMENT les publicités qui contiennent le domaine exact
        
        Args:
            domain: Domaine à analyser (ex: "ravino.converty.shop")
            
        Returns:
            Liste des publicités FILTRÉES (uniquement celles avec le domaine)
        """
        logger.info(f"📊 Collecte des ads POUR LE DOMAINE: {domain}")
        
        # 1. Collecter TOUTES les ads depuis Apify
        all_ads = self.apify_client.search_ads_by_domain(domain)
        logger.info(f"📥 {len(all_ads)} ads brutes récupérées")
        
        # 2. Filtrer STRICTEMENT pour garder uniquement celles avec le domaine exact
        filtered_ads = self._filter_ads_strictly_by_domain(all_ads, domain)
        
        logger.info(f"✅ {len(filtered_ads)} ads FILTRÉES pour {domain}")
        
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
        
        # 1. Vérifier le lien principal
        link_url = snapshot.get('link_url', '')
        if target_domain in link_url:
            return True
        
        # 2. Vérifier dans les cards (carousel)
        cards = snapshot.get('cards', [])
        for card in cards:
            card_link = card.get('link_url', '')
            if target_domain in card_link:
                return True
        
        # 3. Vérifier la caption
        caption = snapshot.get('caption', '')
        if target_domain in caption:
            return True
        
        return False