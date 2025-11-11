"""
Classification des publicités: CONVERTY vs CONCURRENT
"""
from typing import Dict, Any, Optional, List
import re
from urllib.parse import urlparse
from src.classification.dns_checker import DNSChecker
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class URLClassifier:
    """Classifier pour identifier CONVERTY vs CONCURRENT"""
    
    # Domaines à ignorer (pas des concurrents commerciaux)
    IGNORED_DOMAINS = [
        'facebook.com',
        'instagram.com',
        'fb.com',
        'fb.me',
        'bit.ly',
        'tinyurl.com',
        'l.facebook.com',
        'l.instagram.com',
    ]
    
    def __init__(self):
        self.dns_checker = DNSChecker()

    def classify_ad(
        self, 
        ad: Dict[str, Any], 
        converty_domain: str
    ) -> Dict[str, Any]:
        """
        Classifier une publicité avec vérification DNS (logique optimisée)
        
        Args:
            ad: Données de la publicité
            converty_domain: Domaine Converty du client (ex: "echraqa.shop")
            
        Returns:
            {
                'classification': 'CONVERTY' | 'CONCURRENT' | 'UNKNOWN',
                'confidence': 'high' | 'medium' | 'low',
                'reason': str,
                'destination_url': str,
                'competitor_domain': str | None,
                'competitor_platform': str | None
            }
        """
        # Extraire les URLs de la publicité
        urls = self._extract_urls_from_ad(ad)
        
        if not urls:
            return {
                'classification': 'UNKNOWN',
                'confidence': 'low',
                'reason': 'Aucune URL trouvée dans la publicité',
                'destination_url': None,
                'competitor_domain': None,
                'competitor_platform': None
            }
        
        # Analyser chaque URL
        for url in urls:
            # Extraire le domaine
            domain = self._extract_domain(url)
            
            if not domain or self._is_ignored_domain(domain):
                continue
            
            # 🔥 NOUVELLE LOGIQUE DNS (Cascade optimisée)
            dns_result = self.dns_checker.check_domain(domain)
            
            # 1️⃣ Si DNS confirme Converty (IP ou CNAME)
            if dns_result['is_converty']:
                reason_parts = [f"Domaine Converty confirmé par DNS"]
                if dns_result['ip'] == self.dns_checker.CONVERTY_IP:
                    reason_parts.append(f"IP: {dns_result['ip']}")
                elif dns_result['cname']:
                    reason_parts.append(f"CNAME: {dns_result['cname']}")
                
                return {
                    'classification': 'CONVERTY',
                    'confidence': dns_result['confidence'],
                    'reason': ' - '.join(reason_parts),
                    'destination_url': url,
                    'competitor_domain': None,
                    'competitor_platform': 'converty'
                }
            
            # 2️⃣ Si DNS révèle un concurrent (YouCan, Shopify, etc.)
            if dns_result['platform'] != 'unknown':
                return {
                    'classification': 'CONCURRENT',
                    'confidence': dns_result['confidence'],
                    'reason': f"Concurrent détecté: {domain} (Plateforme: {dns_result['platform']})",
                    'destination_url': url,
                    'competitor_domain': domain,
                    'competitor_platform': dns_result['platform']
                }
            
            # 3️⃣ Fallback: Vérifier si l'URL contient le domaine client
            if converty_domain.lower() in url.lower():
                return {
                    'classification': 'CONVERTY',
                    'confidence': 'medium',
                    'reason': f'URL contient le domaine client: {converty_domain}',
                    'destination_url': url,
                    'competitor_domain': None,
                    'competitor_platform': 'converty'
                }
            
            # 4️⃣ Domaine externe non identifié = concurrent unknown
            return {
                'classification': 'CONCURRENT',
                'confidence': 'low',
                'reason': f'Domaine externe non identifié: {domain}',
                'destination_url': url,
                'competitor_domain': domain,
                'competitor_platform': 'unknown'
            }
        
        # Aucune URL commerciale trouvée
        return {
            'classification': 'UNKNOWN',
            'confidence': 'low',
            'reason': 'Aucune URL commerciale identifiée',
            'destination_url': urls[0] if urls else None,
            'competitor_domain': None,
            'competitor_platform': None
        }

    def _extract_urls_from_ad(self, ad: Dict[str, Any]) -> List[str]:
        """
        Extraire toutes les URLs d'une publicité
        
        Args:
            ad: Données de la publicité
            
        Returns:
            Liste des URLs trouvées
        """
        urls = []
        snapshot = ad.get('snapshot', {})
        
        # 1. URL principale (link_url)
        link_url = snapshot.get('link_url')
        if link_url:
            urls.append(link_url)
        
        # 2. URLs dans les cards (carousel)
        cards = snapshot.get('cards', [])
        for card in cards:
            card_url = card.get('link_url')
            if card_url:
                urls.append(card_url)
        
        # 3. Caption
        caption = snapshot.get('caption', '')
        if caption:
            found_urls = re.findall(r'https?://[^\s<>"]+', caption)
            urls.extend(found_urls)
        
        # 4. Body text
        body = snapshot.get('body', {})
        if isinstance(body, dict):
            body_text = body.get('text', '')
        else:
            body_text = str(body)
        
        if body_text:
            found_urls = re.findall(r'https?://[^\s<>"]+', body_text)
            urls.extend(found_urls)
        
        # Éliminer les doublons et nettoyer
        unique_urls = []
        seen = set()
        for url in urls:
            # Nettoyer l'URL
            url = url.strip().rstrip('.,;:!?)')
            if url and url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        return unique_urls

    def _extract_domain(self, url: str) -> Optional[str]:
        """
        Extraire le domaine principal d'une URL
        
        Args:
            url: URL complète
            
        Returns:
            Domaine (ex: "boutique.com")
        """
        try:
            # Parser l'URL
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            parsed = urlparse(url)
            domain = parsed.netloc
            
            if not domain:
                return None
            
            # Nettoyer
            domain = domain.lower()
            domain = domain.replace('www.', '')
            
            # Enlever le port si présent
            if ':' in domain:
                domain = domain.split(':')[0]
            
            return domain if domain else None
            
        except Exception as e:
            logger.debug(f"Erreur extraction domaine de {url}: {e}")
            return None

    def _is_ignored_domain(self, domain: str) -> bool:
        """Vérifier si le domaine doit être ignoré"""
        domain_lower = domain.lower()
        
        for ignored in self.IGNORED_DOMAINS:
            if ignored in domain_lower:
                return True
        
        return False
