"""
Point d'entrée Phase 2: Classification CONVERTY vs CONCURRENT
"""
import json
import glob
import os
import argparse
from src.classification.ad_analyzer import AdAnalyzer
from src.reporting.stats_generator import StatsGenerator
from src.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)


def load_mapping_file(filepath: str) -> dict:
    """Charger un fichier de mapping Phase 1"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """Fonction principale Phase 2"""
    
    # Parser les arguments
    parser = argparse.ArgumentParser(description='Phase 2: Classification des publicités')
    parser.add_argument(
        '--client',
        type=str,
        help='ID du client à analyser (ex: ravino). Si non spécifié, analyse tous les clients.',
        default=None
    )
    args = parser.parse_args()
    
    logger.info("\n" + "="*60)
    logger.info("🚀 PHASE 2: CLASSIFICATION & ANALYSE CONCURRENTS")
    logger.info("="*60 + "\n")
    
    try:
        # Valider la configuration
        settings.validate()
        logger.info("✓ Configuration validée\n")
        
        # Déterminer le pattern de recherche
        if args.client:
            logger.info(f"🎯 Analyse ciblée: client '{args.client}'\n")
            mapping_pattern = os.path.join(settings.MAPPINGS_DIR, f"{args.client}_mapping_*.json")
        else:
            logger.info("📊 Analyse de tous les clients\n")
            mapping_pattern = os.path.join(settings.MAPPINGS_DIR, "*_mapping_*.json")
        
        mapping_files = glob.glob(mapping_pattern)
        
        if not mapping_files:
            if args.client:
                logger.error(f"❌ Aucun fichier de mapping trouvé pour le client: {args.client}")
                logger.error(f"   Cherché dans: {settings.MAPPINGS_DIR}")
                logger.error(f"   Pattern: {args.client}_mapping_*.json")
            else:
                logger.error("❌ Aucun fichier de mapping trouvé")
                logger.error(f"   Cherché dans: {settings.MAPPINGS_DIR}")
            logger.error("\n💡 Lance d'abord la Phase 1:")
            logger.error("   python main.py")
            return
        
        logger.info(f"✓ {len(mapping_files)} fichier(s) de mapping trouvé(s)")
        
        # Afficher les fichiers trouvés
        for mapping_file in mapping_files:
            filename = os.path.basename(mapping_file)
            logger.info(f"  • {filename}")
        
        print()  # Ligne vide
        
        # Créer l'analyseur et le générateur de stats
        analyzer = AdAnalyzer()
        stats_gen = StatsGenerator()
        
        # Analyser chaque client
        for i, mapping_file in enumerate(mapping_files, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"📂 [{i}/{len(mapping_files)}] Traitement: {os.path.basename(mapping_file)}")
            logger.info(f"{'='*60}")
            
            try:
                # Charger le mapping Phase 1
                mapping_data = load_mapping_file(mapping_file)
                
                # Analyser le client
                report = analyzer.analyze_client(mapping_data)
                
                # Sauvegarder le rapport
                output_file = stats_gen.save_classification_report(report)
                
                # Afficher le résumé
                stats_gen.print_summary(report)
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du traitement de {mapping_file}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        logger.info("\n" + "="*60)
        logger.info("✅ PHASE 2 TERMINÉE AVEC SUCCÈS")
        logger.info("="*60)
        logger.info(f"\n📂 Rapports sauvegardés dans: {settings.CLASSIFICATIONS_DIR}\n")
        
    except Exception as e:
        logger.error(f"\n❌ ERREUR GLOBALE: {str(e)}\n")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()