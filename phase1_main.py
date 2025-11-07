"""
Point d'entrée principal - Phase 1: Discovery & Mapping
"""
import json
import os
from config.settings import settings
from src.discovery.site_mapper import SiteMapper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_clients() -> list:
    """
    Charger la liste des clients depuis le fichier JSON
    Format attendu: {"Slug": "...", "Domaine": [...]}
    """
    clients_file = os.path.join(settings.INPUT_DIR, 'clients.json')
    
    with open(clients_file, 'r', encoding='utf-8') as f:
        raw_clients = json.load(f)
    
    normalized_clients = []
    
    for client in raw_clients:
        # Récupérer Slug et Domaine
        slug = client.get('Slug')
        domaines = client.get('Domaine', [])
        
        # Validation
        if not slug:
            logger.warning(f"⚠ Client ignoré (Slug manquant): {client}")
            continue
        
        if not domaines:
            logger.warning(f"⚠ Client {slug} ignoré (aucun domaine)")
            continue
        
        # Nettoyer les domaines
        cleaned_sites = []
        for domaine in domaines:
            # Enlever les espaces
            domaine = domaine.strip()
            
            # Enlever https:// ou http:// si présent
            if domaine.startswith('https://'):
                domaine = domaine[8:]
            elif domaine.startswith('http://'):
                domaine = domaine[7:]
            
            # Enlever les slashes à la fin
            domaine = domaine.rstrip('/')
            
            if domaine:  # Vérifier qu'il reste quelque chose
                cleaned_sites.append(domaine)
        
        if not cleaned_sites:
            logger.warning(f"⚠ Client {slug} ignoré (domaines invalides)")
            continue
        
        # Ajouter le client normalisé
        normalized_clients.append({
            'client_id': slug,
            'sites': cleaned_sites
        })
    
    logger.info(f"✓ {len(normalized_clients)} client(s) chargé(s)")
    
    # Afficher un résumé
    for client in normalized_clients:
        logger.info(f"  • {client['client_id']}: {len(client['sites'])} site(s)")
        for site in client['sites']:
            logger.info(f"    - {site}")
    
    return normalized_clients


def main():
    """Fonction principale"""
    logger.info("\n" + "="*60)
    logger.info("🚀 DÉMARRAGE - PHASE 1: DISCOVERY & MAPPING")
    logger.info("="*60 + "\n")
    
    try:
        # Valider la configuration
        settings.validate()
        logger.info("✓ Configuration validée\n")
        
        # Charger les clients
        logger.info("--- Chargement des clients ---")
        clients = load_clients()
        
        if not clients:
            logger.error("❌ Aucun client valide trouvé dans clients.json")
            logger.error("Format attendu: {\"Slug\": \"...\", \"Domaine\": [...]}")
            return
        
        # Créer le mapper
        mapper = SiteMapper()
        
        # Traiter chaque client
        for client in clients:
            logger.info(f"\n{'#'*60}")
            logger.info(f"# CLIENT: {client['client_id']}")
            logger.info(f"{'#'*60}\n")
            
            # Créer le mapping
            mapping = mapper.map_client_sites(client)
            
            # Sauvegarder
            filepath = mapper.save_mapping(mapping)
            
            # Afficher le résumé
            print_summary(mapping)
        
        logger.info("\n" + "="*60)
        logger.info("✅ PHASE 1 TERMINÉE AVEC SUCCÈS")
        logger.info("="*60 + "\n")
        
    except FileNotFoundError as e:
        logger.error(f"\n❌ Fichier introuvable: {str(e)}")
        logger.error("Assure-toi que data/input/clients.json existe\n")
    except json.JSONDecodeError as e:
        logger.error(f"\n❌ Erreur de format JSON: {str(e)}")
        logger.error("Vérifie la syntaxe de ton fichier clients.json\n")
    except Exception as e:
        logger.error(f"\n❌ ERREUR: {str(e)}\n")
        import traceback
        logger.error(traceback.format_exc())


def print_summary(mapping: dict):
    """Afficher un résumé du mapping"""
    print("\n" + "="*60)
    print(f"📊 RÉSUMÉ - Client: {mapping['client_id']}")
    print("="*60)
    
    for site_mapping in mapping['mappings']:
        print(f"\n🌐 Site: {site_mapping['site']}")
        print(f"   Total ads: {site_mapping['total_ads']}")
        print(f"   Pages FB trouvées: {len(site_mapping['fb_pages'])}")
        
        if site_mapping['fb_pages']:
            for page in site_mapping['fb_pages']:
                print(f"\n   📄 {page['page_name']}")
                print(f"      • ID: {page['page_id']}")
                print(f"      • Ads: {page['ads_count']}")
                print(f"      • Confiance: {page['confidence']}")
        else:
            print(f"   ⚠️  Aucune page Facebook trouvée")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()