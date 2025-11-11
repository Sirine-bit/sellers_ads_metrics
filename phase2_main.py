"""
Point d'entrée Phase 2: Classification CONVERTY vs CONCURRENT
"""
import json
import glob
import os
import argparse
from src.classification.ad_analyzer import AdAnalyzer
from src.reporting.stats_generator import StatsGenerator
from src.database.mongo_client import MongoDBClient  # 🆕 NOUVEAU
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
    parser.add_argument(
        '--no-db',
        action='store_true',
        help='Ne pas sauvegarder dans MongoDB (seulement JSON)',
        default=False
    )
    args = parser.parse_args()
    
    logger.info("\n" + "="*60)
    logger.info("🚀 PHASE 2: CLASSIFICATION & ANALYSE CONCURRENTS")
    logger.info("="*60 + "\n")
    
    # 🆕 Connexion MongoDB
    mongo_client = None
    if not args.no_db:
        try:
            mongo_client = MongoDBClient()
        except Exception as e:
            logger.warning(f"⚠️ MongoDB non disponible, sauvegarde JSON uniquement: {e}")
    
    try:
        # Valider la configuration
        settings.validate()
        logger.info("✓ Configuration validée\n")
        
        # Si MongoDB est disponible, charger les mappings depuis la collection ads_metrics
        mapping_documents = []
        if mongo_client:
            logger.info("📦 Chargement des mappings depuis MongoDB (converty.ads_metrics)")
            query = {}
            if args.client:
                logger.info(f"🎯 Analyse ciblée depuis DB: client '{args.client}'\n")
                query['client_id'] = args.client

            cursor = mongo_client.db['ads_metrics'].find(query).sort('created_at', -1)
            mapping_documents = [d for d in cursor if d.get('mappings')]
            if mapping_documents:
                logger.info(f"✓ {len(mapping_documents)} mapping(s) trouvé(s) dans MongoDB")
            else:
                logger.info("⚠ Aucun mapping trouvé dans MongoDB (fallback vers fichiers JSON)")

        # Fallback: utiliser les fichiers JSON si pas de DB ou si DB vide
        mapping_files = []
        if not mapping_documents:
            # Déterminer le pattern de recherche
            if args.client:
                logger.info(f"🎯 Analyse ciblée (fichiers): client '{args.client}'\n")
                mapping_pattern = os.path.join(settings.MAPPINGS_DIR, f"{args.client}_mapping_*.json")
            else:
                logger.info("📊 Analyse de tous les clients (fichiers)\n")
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
                logger.error("\n💡 Lance d'abord la Phase 1 (ou assure-toi que les mappings sont dans MongoDB):")
                logger.error("   python phase1_main.py")
                return

            logger.info(f"✓ {len(mapping_files)} fichier(s) de mapping trouvé(s)")
            for mapping_file in mapping_files:
                filename = os.path.basename(mapping_file)
                logger.info(f"  • {filename}")

        print()  # Ligne vide
        
        # Créer l'analyseur et le générateur de stats
        analyzer = AdAnalyzer()
        stats_gen = StatsGenerator()
        
        # Analyser chaque client — source: MongoDB si présent, sinon fichiers
        if mapping_documents:
            source_list = mapping_documents
        else:
            source_list = mapping_files

        for i, src in enumerate(source_list, 1):
            if mapping_documents:
                client_label = src.get('client_id') or str(src.get('_id'))
                logger.info(f"\n{'='*60}")
                logger.info(f"📂 [{i}/{len(source_list)}] Traitement depuis DB: {client_label}")
                logger.info(f"{'='*60}")
            else:
                logger.info(f"\n{'='*60}")
                logger.info(f"📂 [{i}/{len(source_list)}] Traitement: {os.path.basename(src)}")
                logger.info(f"{'='*60}")

            try:
                # Charger le mapping Phase 1
                if mapping_documents:
                    mapping_data = src  # document MongoDB
                else:
                    mapping_data = load_mapping_file(src)

                # Analyser le client
                report = analyzer.analyze_client(mapping_data)

                # Sauvegarder JSON local
                output_file = stats_gen.save_classification_report(report)

                # Sauvegarder dans MongoDB (report détaillé)
                if mongo_client and mapping_data.get('mappings'):
                    client_slug = report['client_id']
                    domain = mapping_data['mappings'][0]['site']

                    mongo_id = mongo_client.save_ad_metrics(
                        client_slug=client_slug,
                        domain=domain,
                        report=report
                    )

                    if mongo_id:
                        logger.info(f"💾 Métriques sauvegardées dans MongoDB (ID: {mongo_id})")

                # Afficher le résumé
                stats_gen.print_summary(report)

            except Exception as e:
                src_name = src if not mapping_documents else (src.get('client_id') or str(src.get('_id')))
                logger.error(f"❌ Erreur lors du traitement de {src_name}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        logger.info("\n" + "="*60)
        logger.info("✅ PHASE 2 TERMINÉE AVEC SUCCÈS")
        logger.info("="*60)
        logger.info(f"\n📂 Rapports JSON: {settings.CLASSIFICATIONS_DIR}")
        if mongo_client:
            logger.info(f"💾 Métriques MongoDB: converty.ads_metrics\n")
        
        # Afficher les stats du cache DNS
        print_cache_stats()
        
    except Exception as e:
        logger.error(f"\n❌ ERREUR GLOBALE: {str(e)}\n")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # 🆕 Fermer la connexion MongoDB
        if mongo_client:
            mongo_client.close()


def print_cache_stats():
    """Afficher les statistiques du cache DNS"""
    from src.classification.dns_checker import DNSChecker
    
    stats = DNSChecker.get_cache_stats()
    logger.info("\n" + "="*60)
    logger.info("📊 STATISTIQUES CACHE DNS")
    logger.info("="*60)
    logger.info(f"   Total entrées: {stats['total_entries']}")
    logger.info(f"   Entrées actives: {stats['active_entries']}")
    logger.info(f"   Entrées expirées: {stats['expired_entries']}")
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    main()