"""
Gestionnaire de batches avec persistence et récupération
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BatchManager:
    """Gère le traitement par batch avec sauvegarde et récupération"""
    
    def __init__(self, progress_file: str = "data/output/batch_progress.json"):
        self.progress_file = Path(progress_file)
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        self.progress = self._load_progress()
    
    def _load_progress(self) -> dict:
        """Charger le fichier de progrès existant"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"📂 Progrès chargé: {len(data.get('processed_clients', {}))} clients déjà traités")
                    return data
            except Exception as e:
                logger.warning(f"⚠️ Impossible de charger le progrès: {e}")
        
        return {
            'start_time': datetime.now().isoformat(),
            'last_update': None,
            'processed_clients': {},  # {client_id: {status, timestamp, ...}}
            'batches': [],  # Historique des batches
            'statistics': {
                'total_processed': 0,
                'total_success': 0,
                'total_failed': 0
            }
        }
    
    def _save_progress(self):
        """Sauvegarder le progrès"""
        self.progress['last_update'] = datetime.now().isoformat()
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde progrès: {e}")
    
    def is_client_processed(self, client_id: str) -> bool:
        """Vérifier si un client a déjà été traité avec succès"""
        client_data = self.progress['processed_clients'].get(client_id)
        return client_data is not None and client_data.get('status') == 'success'
    
    def mark_as_processed(self, client_id: str, status: str, 
                         mapping_file: str = None, error: str = None,
                         metadata: dict = None):
        """Marquer un client comme traité"""
        self.progress['processed_clients'][client_id] = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'mapping_file': mapping_file,
            'error': error,
            'metadata': metadata or {}
        }
        
        # Mettre à jour les statistiques
        self.progress['statistics']['total_processed'] += 1
        if status == 'success':
            self.progress['statistics']['total_success'] += 1
        elif status == 'failed':
            self.progress['statistics']['total_failed'] += 1
        
        self._save_progress()
    
    def save_batch_progress(self, batch_number: int, batch_results: dict):
        """Sauvegarder le résultat d'un batch"""
        self.progress['batches'].append({
            'batch_number': batch_number,
            'timestamp': datetime.now().isoformat(),
            'results': batch_results
        })
        self._save_progress()
        logger.info(f"💾 Batch #{batch_number} sauvegardé")
    
    def get_failed_clients(self) -> List[dict]:
        """Récupérer la liste des clients en échec"""
        failed = []
        for client_id, data in self.progress['processed_clients'].items():
            if data['status'] == 'failed':
                failed.append({
                    'client_id': client_id,
                    'error': data.get('error'),
                    'timestamp': data.get('timestamp')
                })
        return failed
    
    def get_next_unprocessed_skip(self, batch_size: int) -> int:
        """
        Calculer le skip pour le prochain batch non traité
        Utile pour reprendre après un arrêt
        """
        processed_count = len([
            c for c in self.progress['processed_clients'].values()
            if c['status'] == 'success'
        ])
        return (processed_count // batch_size) * batch_size
    
    def reset_failed_clients(self):
        """
        Réinitialiser tous les clients en échec pour les retraiter
        """
        failed_count = 0
        for client_id, data in list(self.progress['processed_clients'].items()):
            if data['status'] == 'failed':
                del self.progress['processed_clients'][client_id]
                failed_count += 1
        
        self.progress['statistics']['total_failed'] = 0
        self.progress['statistics']['total_processed'] -= failed_count
        self._save_progress()
        
        logger.info(f"🔄 {failed_count} client(s) en échec réinitialisé(s)")
        return failed_count
    
    def reset_specific_client(self, client_id: str):
        """Réinitialiser un client spécifique"""
        if client_id in self.progress['processed_clients']:
            status = self.progress['processed_clients'][client_id]['status']
            del self.progress['processed_clients'][client_id]
            
            self.progress['statistics']['total_processed'] -= 1
            if status == 'success':
                self.progress['statistics']['total_success'] -= 1
            elif status == 'failed':
                self.progress['statistics']['total_failed'] -= 1
            
            self._save_progress()
            logger.info(f"🔄 Client {client_id} réinitialisé")
            return True
        return False
    
    def get_statistics(self) -> dict:
        """Obtenir les statistiques de traitement"""
        return self.progress['statistics'].copy()
    
    def export_failed_to_json(self, output_file: str = "data/output/failed_clients.json"):
        """Exporter la liste des clients échoués vers un fichier"""
        failed = self.get_failed_clients()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(failed, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 {len(failed)} client(s) échoué(s) exporté(s) vers {output_file}")
        return len(failed)