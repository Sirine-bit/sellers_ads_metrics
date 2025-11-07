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
    ) -> str:
        """
        Sauvegarder le rapport de classification
        
        Args:
            report: Données du rapport
            filename: Nom du fichier (optionnel)
            
        Returns:
            Chemin du fichier créé
        """
        if not filename:
            client_id = report['client_id']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{client_id}_classification_{timestamp}.json"
        
        # Créer le dossier si nécessaire
        os.makedirs(settings.CLASSIFICATIONS_DIR, exist_ok=True)
        
        filepath = os.path.join(settings.CLASSIFICATIONS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Rapport sauvegardé: {filepath}")
        
        return filepath
    
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