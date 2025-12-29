"""
Cache simple pour éviter de re-scraper les mêmes domaines
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SimpleCache:
    """Cache local avec expiration pour les résultats de scraping"""
    
    def __init__(self, cache_dir: str = "data/cache", ttl_days: int = 7):
        """
        Args:
            cache_dir: Dossier de cache
            ttl_days: Durée de validité (défaut: 7 jours)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(days=ttl_days)
    
    def _get_cache_key(self, domain: str) -> str:
        """Générer une clé de cache unique"""
        return hashlib.md5(domain.encode()).hexdigest()
    
    def get(self, domain: str) -> Optional[List[Dict]]:
        """
        Récupérer depuis le cache si valide
        
        Returns:
            Liste des ads ou None si pas en cache/expiré
        """
        cache_key = self._get_cache_key(domain)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Vérifier l'expiration
            cached_at = datetime.fromisoformat(cached_data['cached_at'])
            age = datetime.now() - cached_at
            
            if age > self.ttl:
                logger.info(f"💾 Cache expiré pour {domain} (age: {age.days} jours)")
                cache_file.unlink()  # Supprimer
                return None
            
            logger.info(f"✅ Cache HIT pour {domain} ({len(cached_data['ads'])} ads, age: {age.days} jours)")
            return cached_data['ads']
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur lecture cache: {e}")
            return None
    
    def set(self, domain: str, ads: List[Dict]):
        """Sauvegarder dans le cache"""
        cache_key = self._get_cache_key(domain)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cache_data = {
            'domain': domain,
            'cached_at': datetime.now().isoformat(),
            'ads_count': len(ads),
            'ads': ads
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Cache SAVE pour {domain} ({len(ads)} ads)")
    
    def clear_expired(self) -> int:
        """Nettoyer les caches expirés"""
        cleaned = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                cached_at = datetime.fromisoformat(data['cached_at'])
                if datetime.now() - cached_at > self.ttl:
                    cache_file.unlink()
                    cleaned += 1
            except:
                pass
        
        if cleaned > 0:
            logger.info(f"🧹 {cleaned} caches expirés nettoyés")
        return cleaned
    
    def get_stats(self) -> Dict:
        """Statistiques du cache"""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'total_entries': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }
