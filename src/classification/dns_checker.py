"""
Vérification DNS pour identifier les plateformes e-commerce
"""
import dns.resolver
import socket
from typing import Optional, Dict
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class DNSChecker:
    """Vérificateur DNS pour identifier Converty vs autres plateformes"""
    
    # IP de Converty
    CONVERTY_IP = "34.155.58.152"
    
    # Serveurs DNS connus par plateforme
    PLATFORM_NS = {
        'youcan': ['ns1.youcan.shop', 'ns2.youcan.shop'],
        'shopify': ['shopify.com'],
        'cloudflare': ['cloudflare.com'],
    }
    
    # Cache DNS avec TTL
    _cache: Dict[str, Dict] = {}
    
    @classmethod
    def check_domain(cls, domain: str) -> Dict[str, any]:
        """
        Vérifier un domaine via DNS
        
        Returns:
            {
                'platform': 'converty' | 'youcan' | 'shopify' | 'unknown',
                'is_converty': bool,
                'ip': str,
                'ns_records': list,
                'cname': str | None
            }
        """
        # Nettoyer le domaine
        domain = domain.lower().strip()
        domain = domain.replace('www.', '')
        
        # Vérifier le cache
        if domain in cls._cache:
            cached = cls._cache[domain]
            # TODO: Implémenter TTL
            return cached
        
        result = {
            'platform': 'unknown',
            'is_converty': False,
            'ip': None,
            'ns_records': [],
            'cname': None
        }
        
        try:
            # 1. Vérifier l'IP (A record)
            ip = cls._get_a_record(domain)
            result['ip'] = ip
            
            if ip == cls.CONVERTY_IP:
                result['platform'] = 'converty'
                result['is_converty'] = True
                cls._cache[domain] = result
                return result
            
            # 2. Vérifier CNAME
            cname = cls._get_cname(domain)
            result['cname'] = cname
            
            if cname and 'converty' in cname.lower():
                result['platform'] = 'converty'
                result['is_converty'] = True
                cls._cache[domain] = result
                return result
            
            # 3. Vérifier NS records
            ns_records = cls._get_ns_records(domain)
            result['ns_records'] = ns_records
            
            # Identifier la plateforme via NS
            platform = cls._identify_platform_from_ns(ns_records)
            if platform:
                result['platform'] = platform
                result['is_converty'] = (platform == 'converty')
            
        except Exception as e:
            logger.debug(f"Erreur DNS pour {domain}: {e}")
        
        cls._cache[domain] = result
        return result
    
    @staticmethod
    def _get_a_record(domain: str) -> Optional[str]:
        """Récupérer l'adresse IP (A record)"""
        try:
            ip = socket.gethostbyname(domain)
            return ip
        except Exception:
            return None
    
    @staticmethod
    def _get_cname(domain: str) -> Optional[str]:
        """Récupérer le CNAME"""
        try:
            answers = dns.resolver.resolve(domain, 'CNAME')
            return str(answers[0].target)
        except Exception:
            return None
    
    @staticmethod
    def _get_ns_records(domain: str) -> list:
        """Récupérer les serveurs DNS (NS records)"""
        try:
            answers = dns.resolver.resolve(domain, 'NS')
            return [str(rdata.target) for rdata in answers]
        except Exception:
            return []
    
    @classmethod
    def _identify_platform_from_ns(cls, ns_records: list) -> Optional[str]:
        """Identifier la plateforme via les NS records"""
        ns_str = ' '.join(ns_records).lower()
        
        for platform, markers in cls.PLATFORM_NS.items():
            for marker in markers:
                if marker in ns_str:
                    return platform
        
        return None