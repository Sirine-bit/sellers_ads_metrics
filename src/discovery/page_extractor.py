"""
Extracteur de pages Facebook depuis les publicités FILTRÉES
"""
from typing import List, Dict, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PageExtractor:
    """Extrait les pages Facebook depuis une liste de publicités FILTRÉES"""
    
    @staticmethod
    def extract_pages_from_ads(
        ads: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extraire toutes les pages Facebook uniques depuis les ads FILTRÉES
        
        Args:
            ads: Liste des publicités DÉJÀ FILTRÉES (uniquement celles avec le domaine)
            
        Returns:
            Liste des pages FB qui utilisent le domaine Converty
        """
        logger.info(f"🔍 Extraction des pages depuis {len(ads)} publicités FILTRÉES")
        
        pages_dict = {}
        
        for ad in ads:
            page_id = ad.get('page_id')
            
            if not page_id:
                logger.debug(f"⚠ Ad sans page_id")
                continue
            
            # Si on n'a pas encore vu cette page
            if page_id not in pages_dict:
                pages_dict[page_id] = {
                    'page_id': page_id,
                    'page_name': ad.get('page_name', 'Unknown'),
                    'page_url': ad.get('page_profile_uri', ''),
                    'ads_count': 0,
                    'sample_ad_ids': []
                }
            
            # Incrémenter le compteur d'ads
            pages_dict[page_id]['ads_count'] += 1
            
            # Ajouter un échantillon d'IDs (max 5)
            if len(pages_dict[page_id]['sample_ad_ids']) < 5:
                pages_dict[page_id]['sample_ad_ids'].append(ad.get('ad_archive_id'))
        
        pages_list = list(pages_dict.values())
        
        logger.info(f"✓ {len(pages_list)} pages uniques qui utilisent le domaine")
        
        # Afficher un résumé
        for page in pages_list:
            logger.info(
                f"  • {page['page_name']} "
                f"(ID: {page['page_id']}) - "
                f"{page['ads_count']} ads"
            )
        
        return pages_list