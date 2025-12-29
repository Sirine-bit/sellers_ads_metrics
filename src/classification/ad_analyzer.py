"""
Analyseur complet de publicités pour un client
"""
from typing import Dict, Any, List
from datetime import datetime
from src.classification.url_classifier import URLClassifier
from src.clients.apify_client import ApifyFacebookAdsClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AdAnalyzer:
    """Analyse toutes les publicités d'un client"""
    
    def __init__(self):
        self.classifier = URLClassifier()
        self.apify_client = ApifyFacebookAdsClient()
    
    def analyze_client(self, mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyser toutes les publicités d'un client
        
        Args:
            mapping_data: Données du mapping Phase 1
            
        Returns:
            Rapport complet avec classifications et concurrents
        """
        client_id = mapping_data['client_id']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 PHASE 2: ANALYSE CLIENT - {client_id}")
        logger.info(f"{'='*60}\n")
        
        # 🎯 VÉRIFIER SI LE CLIENT EST ACTIF
        is_active = mapping_data.get('is_active', True)
        phase2_recommendation = mapping_data.get('phase2_recommendation', 'PROCESS')
        total_ads = mapping_data.get('total_ads', 0)
        
        if not is_active or phase2_recommendation == 'SKIP':
            logger.warning(f"\n{'⚠️ '*20}")
            logger.warning(f"⏩ CLIENT INACTIF DÉTECTÉ")
            logger.warning(f"   Client: {client_id}")
            logger.warning(f"   Total ads: {total_ads}")
            logger.warning(f"   Statut: {mapping_data.get('activity_status', 'INACTIF')}")
            logger.warning(f"   💰 ÉCONOMIE: Skip Phase 2 (pas de scraping Apify)")
            logger.warning(f"   📋 Action: Vérification manuelle recommandée")
            logger.warning(f"{'⚠️ '*20}\n")
            
            # Retourner un rapport simplifié
            return {
                'client_id': client_id,
                'analyzed_at': datetime.now().isoformat(),
                'status': 'SKIPPED_INACTIVE',
                'reason': f'Client inactif ({total_ads} ads < {mapping_data.get("activity_threshold", 5)})',
                'total_ads': total_ads,
                'is_active': False,
                'manual_verification_required': True,
                'cost_saved': True
            }
        
        logger.info(f"🟢 Client ACTIF ({total_ads} ads) - Phase 2 en cours...\n")
        
        # Analyser chaque site du mapping
        page_analyses = []
        
        for site_mapping in mapping_data['mappings']:
            converty_domain = site_mapping['site']
            
            logger.info(f"\n{'─'*60}")
            logger.info(f"📍 Domaine Converty: {converty_domain}")
            logger.info(f"{'─'*60}")
            
            # Pour chaque page Facebook trouvée en Phase 1
            for page in site_mapping['fb_pages']:
                page_analysis = self._analyze_page(page, converty_domain)
                page_analyses.append(page_analysis)
        
        # Calculer les statistiques globales
        stats = self._calculate_global_stats(page_analyses)
        
        # Identifier TOUS les concurrents
        all_competitors = self._aggregate_competitors(page_analyses)
        
        # Rapport final
        report = {
            'client_id': client_id,
            'analyzed_at': datetime.now().isoformat(),
            'pages_analyzed': len(page_analyses),
            'global_stats': stats,
            'top_competitors': all_competitors[:20],  # Top 20 concurrents
            'page_details': page_analyses
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ ANALYSE TERMINÉE")
        logger.info(f"   Total concurrents: {len(all_competitors)}")
        logger.info(f"{'='*60}\n")
        
        return report
    
    def _analyze_page(
        self, 
        page: Dict[str, Any], 
        converty_domain: str
    ) -> Dict[str, Any]:
        """
        Analyser TOUTES les publicités d'une page Facebook
        
        Args:
            page: Données de la page (de Phase 1)
            converty_domain: Domaine Converty du client
            
        Returns:
            Analyse complète avec liste des concurrents
        """
        page_id = page['page_id']
        page_name = page['page_name']
        
        logger.info(f"\n📄 Page: {page_name}")
        logger.info(f"   Page ID: {page_id}")
        logger.info(f"   Domaine Converty: {converty_domain}")
        logger.info(f"   📥 Récupération de TOUTES les publicités...")
        
        # Récupérer TOUTES les ads de cette page
        all_page_ads = self.apify_client.get_all_ads_by_page_id(page_id)
        
        logger.info(f"   ✓ {len(all_page_ads)} publicités trouvées")
        logger.info(f"   🔍 Classification en cours...")
        
        # Classifier chaque publicité
        classified_ads = []
        converty_count = 0
        concurrent_count = 0
        unknown_count = 0
        
        # Pour identifier les concurrents (structure corrigée)
        competitors = {}  # {domain: {'count': int, 'platform': str}}
        
        # 🔧 CORRECTION: Boucle avec indentation correcte
        for ad in all_page_ads:
            classification = self.classifier.classify_ad(ad, converty_domain)
            
            classified_ad = {
                'ad_id': ad.get('ad_archive_id'),
                'classification': classification['classification'],
                'confidence': classification['confidence'],
                'reason': classification['reason'],
                'destination_url': classification['destination_url'],
                'competitor_domain': classification.get('competitor_domain'),
                'competitor_platform': classification.get('competitor_platform'),
                'ad_creation_time': ad.get('ad_creation_time'),
                'ad_delivery_start_time': ad.get('ad_delivery_start_time'),
            }
            
            classified_ads.append(classified_ad)
            
            # Compter
            if classification['classification'] == 'CONVERTY':
                converty_count += 1
            elif classification['classification'] == 'CONCURRENT':
                concurrent_count += 1
                # Enregistrer le concurrent avec sa plateforme
                competitor_domain = classification.get('competitor_domain')
                if competitor_domain:
                    if competitor_domain not in competitors:
                        competitors[competitor_domain] = {
                            'count': 0,
                            'platform': classification.get('competitor_platform')
                        }
                    competitors[competitor_domain]['count'] += 1
            else:
                unknown_count += 1
        
        # Calculer les ratios
        total = len(classified_ads)
        converty_ratio = (converty_count / total * 100) if total > 0 else 0
        concurrent_ratio = (concurrent_count / total * 100) if total > 0 else 0
        
        logger.info(f"\n   📊 Résultats:")
        logger.info(f"   ✅ CONVERTY: {converty_count} ({converty_ratio:.1f}%)")
        logger.info(f"   ⚠️  CONCURRENT: {concurrent_count} ({concurrent_ratio:.1f}%)")
        logger.info(f"   ❓ UNKNOWN: {unknown_count}")
        
        # Afficher les concurrents
        if competitors:
            logger.info(f"\n   🎯 Concurrents identifiés pour cette page:")
            sorted_competitors = sorted(
                competitors.items(), 
                key=lambda x: x[1]['count'], 
                reverse=True
            )
            for domain, data in sorted_competitors[:5]:
                platform = data['platform'] or 'unknown'
                logger.info(f"      • {domain} ({platform}): {data['count']} ads")
        
        return {
            'page_id': page_id,
            'page_name': page_name,
            'converty_domain': converty_domain,
            'total_ads': total,
            'converty_ads': converty_count,
            'concurrent_ads': concurrent_count,
            'unknown_ads': unknown_count,
            'converty_ratio': converty_ratio,
            'concurrent_ratio': concurrent_ratio,
            'competitors': [
                {
                    'domain': domain, 
                    'ads_count': data['count'],
                    'platform': data['platform']
                }
                for domain, data in sorted(
                    competitors.items(), 
                    key=lambda x: x[1]['count'], 
                    reverse=True
                )
            ],
            'classified_ads': classified_ads
        }
    
    def _calculate_global_stats(self, page_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculer les statistiques globales"""
        total_ads = sum(p['total_ads'] for p in page_analyses)
        total_converty = sum(p['converty_ads'] for p in page_analyses)
        total_concurrent = sum(p['concurrent_ads'] for p in page_analyses)
        total_unknown = sum(p['unknown_ads'] for p in page_analyses)
        
        converty_ratio = (total_converty / total_ads * 100) if total_ads > 0 else 0
        concurrent_ratio = (total_concurrent / total_ads * 100) if total_ads > 0 else 0
        
        return {
            'total_ads': total_ads,
            'converty_ads': total_converty,
            'concurrent_ads': total_concurrent,
            'unknown_ads': total_unknown,
            'converty_ratio': round(converty_ratio, 2),
            'concurrent_ratio': round(concurrent_ratio, 2)
        }
    
    def _aggregate_competitors(self, page_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Agréger tous les concurrents trouvés sur toutes les pages"""
        all_competitors = {}  # {domain: {'count': int, 'platform': str}}
        
        for page_analysis in page_analyses:
            for competitor in page_analysis.get('competitors', []):
                domain = competitor['domain']
                count = competitor['ads_count']
                platform = competitor.get('platform')
                
                if domain in all_competitors:
                    all_competitors[domain]['count'] += count
                    # Garder la plateforme si elle existe
                    if not all_competitors[domain]['platform'] and platform:
                        all_competitors[domain]['platform'] = platform
                else:
                    all_competitors[domain] = {
                        'count': count,
                        'platform': platform
                    }
        
        # Trier par nombre d'ads (décroissant)
        sorted_competitors = [
            {
                'domain': domain, 
                'total_ads': data['count'],
                'platform': data['platform']
            }
            for domain, data in sorted(
                all_competitors.items(), 
                key=lambda x: x[1]['count'], 
                reverse=True
            )
        ]
        
        return sorted_competitors