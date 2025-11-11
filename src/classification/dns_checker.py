"""
Vérification DNS pour identifier les plateformes e-commerce
"""
import dns.resolver
import socket
import time
from typing import Optional, Dict
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class DNSChecker:
    """Vérificateur DNS pour identifier Converty vs autres plateformes"""
    
    # IP de Converty
    CONVERTY_IP = "34.155.58.152"
    
    # Patterns pour identifier les plateformes
    PLATFORM_PATTERNS = {
        'converty': {
            'cname': ['converty.shop', 'converty.site'],
            'ns': []  # Converty n'a pas de NS spécifiques
        },
        'youcan': {
            'cname': ['youcan.shop'],
            'ns': ['ns1.youcan.shop', 'ns2.youcan.shop']
        },
        'shopify': {
            'cname': ['shopify.com', 'myshopify.com'],
            'ns': ['shopify.com']
        },
        'woocommerce': {
            'cname': [],
            'ns': []  # Pas de pattern spécifique
        }
    }
    
    # Cache DNS avec TTL (600s = 10 minutes)
    _cache: Dict[str, Dict] = {}
    _cache_ttl = 600  # secondes
    
    @classmethod
    def check_domain(cls, domain: str) -> Dict[str, any]:
        """
        Vérifier un domaine via DNS avec cache
        
        Returns:
            {
                'platform': 'converty' | 'youcan' | 'shopify' | 'unknown',
                'is_converty': bool,
                'ip': str | None,
                'ns_records': list,
                'cname': str | None,
                'confidence': 'high' | 'medium' | 'low',
                'cached': bool
            }
        """
        # Nettoyer le domaine
        domain = domain.lower().strip().replace('www.', '')
        
        # ✅ CHECK CACHE AVEC TTL
        if domain in cls._cache:
            cached_entry = cls._cache[domain]
            cache_age = time.time() - cached_entry.get('timestamp', 0)
            
            if cache_age < cls._cache_ttl:
                logger.debug(f"🔄 Cache hit pour {domain} (age: {int(cache_age)}s)")
                result = cached_entry['data'].copy()
                result['cached'] = True
                return result
            else:
                # Cache expiré, on le supprime
                logger.debug(f"⏰ Cache expiré pour {domain}")
                del cls._cache[domain]
        
        # Initialiser le résultat
        result = {
            'platform': 'unknown',
            'is_converty': False,
            'ip': None,
            'ns_records': [],
            'cname': None,
            'confidence': 'low',
            'cached': False
        }
        
        try:
            # 1️⃣ CHECK IP (A Record) - Si match direct Converty
            ip = cls._get_a_record(domain)
            result['ip'] = ip
            
            if ip == cls.CONVERTY_IP:
                result['platform'] = 'converty'
                result['is_converty'] = True
                result['confidence'] = 'high'
                cls._save_to_cache(domain, result)
                logger.debug(f"✅ {domain} → CONVERTY (IP match)")
                return result
            
            # 2️⃣ CHECK CNAME - Peut révéler Converty via CDN OU concurrent
            cname = cls._get_cname(domain)
            result['cname'] = cname
            
            if cname:
                cname_lower = cname.lower()
                
                # Check Converty dans CNAME
                for pattern in cls.PLATFORM_PATTERNS['converty']['cname']:
                    if pattern in cname_lower:
                        result['platform'] = 'converty'
                        result['is_converty'] = True
                        result['confidence'] = 'high'
                        cls._save_to_cache(domain, result)
                        logger.debug(f"✅ {domain} → CONVERTY (CNAME: {cname})")
                        return result
                
                # Check YouCan dans CNAME
                for pattern in cls.PLATFORM_PATTERNS['youcan']['cname']:
                    if pattern in cname_lower:
                        result['platform'] = 'youcan'
                        result['confidence'] = 'high'
                        cls._save_to_cache(domain, result)
                        logger.debug(f"⚠️ {domain} → CONCURRENT (YouCan via CNAME)")
                        return result
                
                # Check Shopify dans CNAME
                for pattern in cls.PLATFORM_PATTERNS['shopify']['cname']:
                    if pattern in cname_lower:
                        result['platform'] = 'shopify'
                        result['confidence'] = 'high'
                        cls._save_to_cache(domain, result)
                        logger.debug(f"⚠️ {domain} → CONCURRENT (Shopify via CNAME)")
                        return result
            
            # 3️⃣ CHECK NS RECORDS - Si CNAME n'a rien révélé
            ns_records = cls._get_ns_records(domain)
            result['ns_records'] = ns_records
            
            if ns_records:
                ns_str = ' '.join(ns_records).lower()
                
                # Check YouCan NS
                for pattern in cls.PLATFORM_PATTERNS['youcan']['ns']:
                    if pattern in ns_str:
                        result['platform'] = 'youcan'
                        result['confidence'] = 'medium'
                        cls._save_to_cache(domain, result)
                        logger.debug(f"⚠️ {domain} → CONCURRENT (YouCan via NS)")
                        return result
                
                # Check Shopify NS
                for pattern in cls.PLATFORM_PATTERNS['shopify']['ns']:
                    if pattern in ns_str:
                        result['platform'] = 'shopify'
                        result['confidence'] = 'medium'
                        cls._save_to_cache(domain, result)
                        logger.debug(f"⚠️ {domain} → CONCURRENT (Shopify via NS)")
                        return result
            
            # 4️⃣ Aucun pattern trouvé → unknown
            result['platform'] = 'unknown'
            result['confidence'] = 'low'
            cls._save_to_cache(domain, result)
            logger.debug(f"❓ {domain} → UNKNOWN (aucun pattern DNS)")
            
        except Exception as e:
            logger.debug(f"❌ Erreur DNS pour {domain}: {e}")
            # Sauvegarder même les erreurs dans le cache pour éviter de réessayer
            cls._save_to_cache(domain, result)
        
        return result
    
    @classmethod
    def _save_to_cache(cls, domain: str, result: Dict) -> None:
        """Sauvegarder dans le cache avec timestamp"""
        cls._cache[domain] = {
            'data': result.copy(),
            'timestamp': time.time()
        }
    
    @classmethod
    def clear_cache(cls) -> None:
        """Vider le cache (utile pour les tests)"""
        cls._cache.clear()
        logger.info("🗑️ Cache DNS vidé")
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, int]:
        """Obtenir les stats du cache"""
        total = len(cls._cache)
        expired = 0
        current_time = time.time()
        
        for entry in cls._cache.values():
            age = current_time - entry.get('timestamp', 0)
            if age >= cls._cache_ttl:
                expired += 1
        
        return {
            'total_entries': total,
            'expired_entries': expired,
            'active_entries': total - expired
        }
    
    @staticmethod
    def _get_a_record(domain: str) -> Optional[str]:
        """Récupérer l'adresse IP (A record)"""
        try:
            ip = socket.gethostbyname(domain)
            return ip
        except Exception as e:
            logger.debug(f"Pas d'A record pour {domain}: {e}")
            return None
    
    @staticmethod
    def _get_cname(domain: str) -> Optional[str]:
        """Récupérer le CNAME"""
        try:
            answers = dns.resolver.resolve(domain, 'CNAME')
            cname = str(answers[0].target).rstrip('.')
            return cname
        except dns.resolver.NoAnswer:
            logger.debug(f"Pas de CNAME pour {domain}")
            return None
        except Exception as e:
            logger.debug(f"Erreur CNAME pour {domain}: {e}")
            return None
    
    @staticmethod
    def _get_ns_records(domain: str) -> list:
        """Récupérer les serveurs DNS (NS records)"""
        try:
            answers = dns.resolver.resolve(domain, 'NS')
            ns_list = [str(rdata.target).rstrip('.') for rdata in answers]
            return ns_list
        except Exception as e:
            logger.debug(f"Pas de NS records pour {domain}: {e}")
            return []