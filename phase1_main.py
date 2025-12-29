"""
Point d'entrée principal - Phase 1: Discovery & Mapping
"""
import json
import time
from datetime import datetime
from config.settings import settings
from src.database.mongo_client import MongoDBClient
from src.discovery.site_mapper import SiteMapper
from src.utils.logger import setup_logger
from src.utils.batch_manager import BatchManager
from src.utils.cost_tracker import CostTracker
from src.utils.mapper_saver import MongoMapperSaver

logger = setup_logger(__name__)


def load_clients_batch(skip: int = 0, limit: int = 30) -> list:
    """
    Charger un batch de clients depuis MongoDB
    """
    mongo_client = MongoDBClient()
    stores = list(mongo_client.db.stores.find().skip(skip).limit(limit))
    
    logger.info(f"🔍 Batch: {len(stores)} clients (skip={skip}, limit={limit})")
    normalized_clients = []
    
    for store in stores:
        slug = store.get('slug')
        domain = store.get('domain')
        
        if not domain:
            domain = f"{slug}.converty.shop"
        
        domaines = [domain] if domain else []
        
        if not slug or not domaines:
            logger.warning(f"⚠ Client ignoré: {slug}")
            continue
        
        # Nettoyer les domaines
        cleaned_sites = []
        for domaine in domaines:
            domaine = domaine.strip()
            if domaine.startswith('https://'):
                domaine = domaine[8:]
            elif domaine.startswith('http://'):
                domaine = domaine[7:]
            domaine = domaine.rstrip('/')
            
            if domaine:
                cleaned_sites.append(domaine)
        
        if not cleaned_sites:
            continue
        
        normalized_clients.append({
            'client_id': slug,
            'sites': cleaned_sites
        })
    
    return normalized_clients


def process_batch(batch_number: int, clients: list, mapper: SiteMapper, 
                  batch_manager: BatchManager, cost_tracker: CostTracker,
                  mongo_saver: MongoMapperSaver):
    """Traiter un batch de clients avec sauvegarde MongoDB"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📦 BATCH #{batch_number} - {len(clients)} clients")
    logger.info(f"{'='*60}\n")
    
    # Marquer le début du batch pour le coût
    cost_tracker.start_batch()
    
    batch_results = {
        'batch_number': batch_number,
        'total_clients': len(clients),
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'clients': []
    }
    
    for idx, client in enumerate(clients, 1):
        client_id = client['client_id']
        logger.info(f"\n[{idx}/{len(clients)}] 🔄 Traitement: {client_id}")
        
        # Vérifier si déjà traité dans MongoDB
        if mongo_saver.is_already_processed(client_id):
            logger.info(f"✅ {client_id} déjà dans MongoDB, skip")
            batch_results['clients'].append({
                'client_id': client_id,
                'mapping_done': True,
                'status': 'skipped',
                'message': 'Déjà dans MongoDB'
            })
            batch_results['skipped'] += 1
            continue
        
        try:
            # Traiter le client
            mapping = mapper.map_client_sites(client)
            
            # Préparer les métadonnées
            processing_metadata = {
                'batch_number': batch_number,
                'processing_timestamp': datetime.now().isoformat(),
                'sites_count': len(client['sites']),
                'total_ads': sum(m['total_ads'] for m in mapping['mappings']),
                'fb_pages_found': sum(len(m['fb_pages']) for m in mapping['mappings'])
            }
            
            # Sauvegarder dans MongoDB
            success = mongo_saver.save_mapping(mapping, processing_metadata)
            
            if not success:
                raise Exception("Échec sauvegarde MongoDB")
            
            # Enregistrer dans le batch manager
            batch_manager.mark_as_processed(
                client_id=client_id,
                status='success',
                mapping_file=f"mongodb://ads_metrics/{client_id}",
                metadata=processing_metadata
            )
            
            # Enregistrer le client dans le cost tracker
            cost_tracker.record_client(client_id, processing_metadata)
            
            batch_results['clients'].append({
                'client_id': client_id,
                'mapping_done': True,
                'status': 'success',
                'sites_processed': len(client['sites']),
                'total_ads': processing_metadata['total_ads'],
                'fb_pages': processing_metadata['fb_pages_found']
            })
            batch_results['successful'] += 1
            
            logger.info(f"✅ {client_id} traité et sauvegardé dans MongoDB")
            
        except Exception as e:
            logger.error(f"❌ Erreur sur {client_id}: {str(e)}")
            
            # Marquer comme échoué dans MongoDB
            mongo_saver.mark_as_failed(
                client_id=client_id,
                error=str(e),
                processing_metadata={
                    'batch_number': batch_number,
                    'error_timestamp': datetime.now().isoformat()
                }
            )
            
            # Enregistrer l'échec
            batch_manager.mark_as_processed(
                client_id=client_id,
                status='failed',
                error=str(e)
            )
            
            batch_results['clients'].append({
                'client_id': client_id,
                'mapping_done': False,
                'status': 'failed',
                'error': str(e)
            })
            batch_results['failed'] += 1
    
    # Enregistrer le coût du batch
    cost_tracker.end_batch(batch_number, len(clients))
    
    return batch_results


def main():
    """Fonction principale"""
    logger.info("\n" + "="*60)
    logger.info("🚀 DÉMARRAGE - PHASE 1: DISCOVERY & MAPPING")
    logger.info("📊 Sauvegarde: MongoDB (converty.ads_metrics)")
    logger.info("💰 Coûts: API Apify RÉELS")
    logger.info("="*60 + "\n")
    
    try:
        # Valider la configuration
        settings.validate()
        logger.info("✓ Configuration validée\n")
        
        # Initialiser les gestionnaires
        batch_manager = BatchManager()
        cost_tracker = CostTracker(budget_limit=5.0)
        mongo_saver = MongoMapperSaver()
        mapper = SiteMapper()
        
        # Paramètres du batch
        BATCH_SIZE = 30
        batch_number = 1
        skip = 0
        
        # Compter le total de clients
        mongo_client = MongoDBClient()
        total_clients = mongo_client.db.stores.count_documents({})
        total_batches = (total_clients + BATCH_SIZE - 1) // BATCH_SIZE
        
        logger.info(f"📊 Total clients dans MongoDB: {total_clients}")
        logger.info(f"📦 Nombre de batches prévus: {total_batches}")
        logger.info(f"💰 Budget Apify: ${cost_tracker.budget_limit}\n")
        
        # Afficher les statistiques MongoDB
        mongo_stats = mongo_saver.get_statistics()
        logger.info(f"📈 Déjà dans ads_metrics: {mongo_stats.get('total_clients', 0)} clients")
        if mongo_stats.get('by_status'):
            for status, data in mongo_stats['by_status'].items():
                logger.info(f"   • {status}: {data['count']} clients")
        print()
        
        all_batch_results = []
        
        # Traiter les batches
        while True:
            # Vérifier le budget RÉEL
            if cost_tracker.is_budget_exceeded():
                session_cost = cost_tracker.get_session_cost()
                logger.warning(f"\n⚠️ BUDGET DÉPASSÉ: ${session_cost:.2f}/${cost_tracker.budget_limit}")
                logger.warning("Arrêt du traitement pour éviter les frais supplémentaires\n")
                break
            
            # Charger le batch
            clients = load_clients_batch(skip=skip, limit=BATCH_SIZE)
            
            if not clients:
                logger.info("\n✅ Tous les clients ont été traités")
                break
            
            # Traiter le batch
            batch_results = process_batch(
                batch_number=batch_number,
                clients=clients,
                mapper=mapper,
                batch_manager=batch_manager,
                cost_tracker=cost_tracker,
                mongo_saver=mongo_saver
            )
            
            all_batch_results.append(batch_results)
            
            # Afficher le résumé du batch
            print_batch_summary(batch_results, cost_tracker)
            
            # Sauvegarder le progrès du batch
            batch_manager.save_batch_progress(batch_number, batch_results)
            
            # Préparer le prochain batch
            skip += BATCH_SIZE
            batch_number += 1
            
            # Pause entre les batches (pour rate limiting)
            time.sleep(2)
        
        # Résumé final
        print_final_summary(all_batch_results, cost_tracker, batch_manager, mongo_saver)
        
        logger.info("\n" + "="*60)
        logger.info("✅ PHASE 1 TERMINÉE")
        logger.info("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"\n❌ ERREUR CRITIQUE: {str(e)}\n")
        import traceback
        logger.error(traceback.format_exc())


def print_batch_summary(batch_results: dict, cost_tracker: CostTracker):
    """Afficher le résumé d'un batch"""
    batch_cost = cost_tracker.get_batch_cost()
    session_cost = cost_tracker.get_session_cost()
    
    print("\n" + "="*60)
    print(f"📊 RÉSUMÉ BATCH #{batch_results['batch_number']}")
    print("="*60)
    print(f"✅ Succès: {batch_results['successful']}/{batch_results['total_clients']}")
    print(f"⏭️  Skipped: {batch_results['skipped']}/{batch_results['total_clients']}")
    print(f"❌ Échecs: {batch_results['failed']}/{batch_results['total_clients']}")
    print(f"💰 Coût batch (RÉEL Apify): ${batch_cost:.4f}")
    print(f"💰 Coût session: ${session_cost:.4f}/${cost_tracker.budget_limit}")
    print(f"📈 Budget restant: ${cost_tracker.get_remaining_budget():.2f}")
    print("="*60 + "\n")


def print_final_summary(all_batches: list, cost_tracker: CostTracker, 
                       batch_manager: BatchManager, mongo_saver: MongoMapperSaver):
    """Afficher le résumé final"""
    total_success = sum(b['successful'] for b in all_batches)
    total_failed = sum(b['failed'] for b in all_batches)
    total_skipped = sum(b['skipped'] for b in all_batches)
    total_clients = sum(b['total_clients'] for b in all_batches)
    
    session_cost = cost_tracker.get_session_cost()
    
    print("\n" + "="*60)
    print("📊 RÉSUMÉ FINAL - TOUS LES BATCHES")
    print("="*60)
    print(f"📦 Nombre de batches traités: {len(all_batches)}")
    print(f"👥 Total clients: {total_clients}")
    print(f"✅ Succès: {total_success} ({total_success/total_clients*100:.1f}%)")
    print(f"⏭️  Skipped: {total_skipped} ({total_skipped/total_clients*100:.1f}%)")
    print(f"❌ Échecs: {total_failed} ({total_failed/total_clients*100:.1f}%)")
    print(f"\n💰 COÛTS APIFY RÉELS:")
    print(f"   Session: ${session_cost:.4f}")
    print(f"   Moyen/client: ${session_cost/total_success:.4f}" if total_success > 0 else "N/A")
    print("="*60)
    
    # Statistiques MongoDB
    mongo_stats = mongo_saver.get_statistics()
    print(f"\n📊 MONGODB (ads_metrics):")
    print(f"   Total documents: {mongo_stats.get('total_clients', 0)}")
    if mongo_stats.get('by_status'):
        for status, data in mongo_stats['by_status'].items():
            print(f"   • {status}: {data['count']} ({data.get('total_ads', 0)} ads)")
    
    # Afficher les clients échoués
    failed_clients = batch_manager.get_failed_clients()
    if failed_clients:
        print(f"\n⚠️ {len(failed_clients)} client(s) en échec:")
        for client in failed_clients[:10]:
            print(f"  • {client['client_id']}: {client['error'][:50]}...")
        if len(failed_clients) > 10:
            print(f"  ... et {len(failed_clients) - 10} autres")
    
    print("\n💾 Données sauvegardées:")
    print(f"  • MongoDB: converty.ads_metrics")
    print(f"  • Progrès: data/output/batch_progress.json")
    print(f"  • Coûts: data/output/cost_tracking.json")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()