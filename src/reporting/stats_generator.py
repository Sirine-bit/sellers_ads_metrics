"""
Générateur de statistiques et rapports
"""
import json
import os
from datetime import datetime
from typing import Dict, Any
from config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class StatsGenerator:
    """Génère des rapports statistiques"""
    
    @staticmethod
    def save_classification_report(
        report: Dict[str, Any],
        filename: str = None
    ) -> Dict[str, Any]:
        """
        Préparer le rapport de classification pour MongoDB avec la même structure que les fichiers JSON
        
        Args:
            report: Données du rapport
            filename: Non utilisé, gardé pour compatibilité
            
        Returns:
            Rapport formaté pour MongoDB
        """
        # Calculer les statistiques globales
        total_ads = 0
        converty_ads = 0
        concurrent_ads = 0
        unknown_ads = 0
        competitors = {}
        
        # Analyser les pages et annonces
        page_details = []
        
        for page in report.get('pages', []):
            page_stats = {
                'page_id': page['page_id'],
                'page_name': page['name'],
                'converty_domain': page.get('converty_domain', ''),
                'total_ads': len(page['ads']),
                'converty_ads': sum(1 for ad in page['ads'] if ad['classification'] == 'CONVERTY'),
                'concurrent_ads': sum(1 for ad in page['ads'] if ad['classification'] == 'CONCURRENT'),
                'unknown_ads': sum(1 for ad in page['ads'] if ad['classification'] == 'UNKNOWN')
            }
            
            # Calculer les ratios
            page_stats['converty_ratio'] = round(page_stats['converty_ads'] / page_stats['total_ads'] * 100, 2) if page_stats['total_ads'] > 0 else 0
            page_stats['concurrent_ratio'] = round(page_stats['concurrent_ads'] / page_stats['total_ads'] * 100, 2) if page_stats['total_ads'] > 0 else 0
            
            # Extraire les infos des concurrents
            page_competitors = []
            for ad in page['ads']:
                if ad['classification'] == 'CONCURRENT':
                    domain = ad.get('competitor_domain')
                    if domain:
                        competitors[domain] = competitors.get(domain, 0) + 1
                        
            page_stats['competitors'] = page_competitors
            page_stats['classified_ads'] = [
                {
                    'ad_id': ad['ad_id'],
                    'classification': ad['classification'],
                    'confidence': ad.get('confidence', 'medium'),
                    'reason': ad.get('reason', ''),
                    'destination_url': ad.get('url'),
                    'competitor_domain': ad.get('competitor_domain'),
                    'competitor_platform': ad.get('competitor_platform'),
                    'creation_date': ad.get('creation_date'),
                    'start_date': ad.get('start_date'),
                    'end_date': ad.get('end_date')
                }
                for ad in page['ads']
            ]
            
            page_details.append(page_stats)
            
            # Mettre à jour les totaux globaux
            total_ads += page_stats['total_ads']
            converty_ads += page_stats['converty_ads']
            concurrent_ads += page_stats['concurrent_ads']
            unknown_ads += page_stats['unknown_ads']
            
        # Préparer les top concurrents
        top_competitors = [
            {
                'domain': domain,
                'total_ads': count,
                'platform': 'unknown'
            }
            for domain, count in sorted(competitors.items(), key=lambda x: x[1], reverse=True)
        ]
            
        # Créer le rapport pour MongoDB avec la même structure que les fichiers JSON
        mongo_report = {
            'client_id': report['client_id'],
            'analyzed_at': datetime.now().isoformat(),
            'pages_analyzed': len(page_details),
            'global_stats': {
                'total_ads': total_ads,
                'converty_ads': converty_ads,
                'concurrent_ads': concurrent_ads,
                'unknown_ads': unknown_ads,
                'converty_ratio': round(converty_ads / total_ads * 100, 2) if total_ads > 0 else 0,
                'concurrent_ratio': round(concurrent_ads / total_ads * 100, 2) if total_ads > 0 else 0
            },
            'top_competitors': top_competitors,
            'page_details': page_details,
            'type': 'report'  # Marquer comme rapport (Phase 2)
        }
        
        return mongo_report
    
    @staticmethod
    def print_summary(report: Dict[str, Any]):
        """Afficher un résumé du rapport"""
        stats = report['global_stats']
        
        print("\n" + "="*60)
        print(f"📊 RÉSUMÉ - Client: {report['client_id']}")
        print("="*60)
        
        print(f"\n📈 Statistiques globales:")
        print(f"   • Total publicités analysées: {stats['total_ads']}")
        print(f"   • CONVERTY: {stats['converty_ads']} ({stats['converty_ratio']}%)")
        print(f"   • CONCURRENT: {stats['concurrent_ads']} ({stats['concurrent_ratio']}%)")
        print(f"   • UNKNOWN: {stats['unknown_ads']}")
        
        # Top concurrents
        top_competitors = report.get('top_competitors', [])
        if top_competitors:
            print(f"\n🎯 Top 10 Concurrents:")
            for i, comp in enumerate(top_competitors[:10], 1):
                print(f"   {i}. {comp['domain']}: {comp['total_ads']} ads")
        
        # Détails par page
        print(f"\n📄 Détails par page Facebook:")
        for page in report['page_details']:
            print(f"\n   {page['page_name']} (ID: {page['page_id']})")
            print(f"      • Total ads: {page['total_ads']}")
            print(f"      • CONVERTY: {page['converty_ads']} ({page['converty_ratio']:.1f}%)")
            print(f"      • CONCURRENT: {page['concurrent_ads']} ({page['concurrent_ratio']:.1f}%)")
            
            # Concurrents de cette page
            if page['competitors']:
                print(f"      • Concurrents (top 3):")
                for comp in page['competitors'][:3]:
                    print(f"         - {comp['domain']}: {comp['ads_count']} ads")
        
        print("\n" + "="*60 + "\n")