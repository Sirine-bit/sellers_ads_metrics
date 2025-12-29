"""
Point d'entrée Phase 2: Classification CONVERTY vs CONCURRENT
"""
import json
import argparse
from src.classification.ad_analyzer import AdAnalyzer
from src.reporting.stats_generator import StatsGenerator
from src.database.mongo_client import MongoDBClient
from src.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)


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
    
    # Connexion MongoDB (obligatoire)
    mongo_client = None
    if not args.no_db:
        try:
            mongo_client = MongoDBClient()
        except Exception as e:
            logger.warning(f"⚠️ MongoDB non disponible, sauvegarde JSON uniquement: {e}")
    if args.no_db or not mongo_client:
        logger.error("MongoDB requis pour Phase 2 (pas de fallback fichiers)")
        return
    
    try:
        # Valider la configuration
        settings.validate()
        logger.info("✓ Configuration validée\n")
        
        # Charger uniquement les documents de type 'mapping' et status 'active'
        logger.info("📦 Chargement des mappings depuis MongoDB (converty.ads_metrics)")
        query = {'status': 'active', 'type': 'mapping'}
        if args.client:
            logger.info(f"🎯 Analyse ciblée depuis DB: client '{args.client}'\n")
            query['client_id'] = args.client
        else:
            logger.info("🟢 Chargement des clients ACTIFS uniquement (status='active')\n")

        cursor = mongo_client.db['ads_metrics'].find(query).sort('timestamp', -1)
        mapping_documents = list(cursor)
        logger.info(f"Docs actifs type='mapping' trouvés: {len(mapping_documents)}")
        if not mapping_documents:
            logger.error("❌ Aucun document actif de type 'mapping' pour ce filtre")
            logger.error(f"Requête: {query}")
            return
        logger.info(f"✓ {len(mapping_documents)} document(s) prêt(s) à traiter")

        print()  # Ligne vide
        
        # Créer l'analyseur et le générateur de stats
        analyzer = AdAnalyzer()
        stats_gen = StatsGenerator()
        
        # Analyser chaque client (MongoDB uniquement)
        source_list = mapping_documents

        for i, src in enumerate(source_list, 1):
            client_label = src.get('client_id') or str(src.get('_id'))
            logger.info(f"\n{'='*60}")
            logger.info(f"📂 [{i}/{len(source_list)}] Traitement depuis DB: {client_label}")
            logger.info(f"{'='*60}")

            try:
                # Charger le mapping Phase 1 depuis MongoDB
                mapping_data = src

                # Normaliser la clé des mappings (Phase 1 peut stocker 'sites_mapping')
                if not mapping_data.get('mappings') and mapping_data.get('sites_mapping'):
                    mapping_data['mappings'] = mapping_data['sites_mapping']

                # Fallback sur total_ads depuis processing_metadata si absent
                if 'total_ads' not in mapping_data and mapping_data.get('processing_metadata'):
                    mapping_data['total_ads'] = mapping_data['processing_metadata'].get('total_ads', 0)

                # Vérifier la présence finale de 'mappings'
                if not mapping_data.get('mappings'):
                    logger.warning(f"⏭️ Skip {client_label}: champ 'mappings' absent")
                    continue

                # Analyser le client
                report = analyzer.analyze_client(mapping_data)

                # Sauvegarder JSON local
                output_file = stats_gen.save_classification_report(report)

                # Sauvegarder dans MongoDB (report détaillé)
                if mongo_client and mapping_data.get('mappings'):
                    client_slug = report['client_id']
                    domain = mapping_data['mappings'][0].get('site')

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