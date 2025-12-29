"""
Tracker de coûts Apify RÉELS via l'API Apify
"""
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from apify_client import ApifyClient
from src.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)


class CostTracker:
    """Gère le suivi des coûts RÉELS Apify via l'API"""
    
    def __init__(self, budget_limit: float = 5.0, 
                 tracking_file: str = "data/output/cost_tracking.json"):
        self.budget_limit = budget_limit
        self.tracking_file = Path(tracking_file)
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load_tracking()
        
        # Initialiser le client Apify officiel
        self.apify_token = settings.APIFY_API_TOKEN
        
        if not self.apify_token:
            logger.error("❌ APIFY_API_TOKEN non configuré dans .env")
            self.apify_client = None
            self.initial_usage = 0.0
        else:
            try:
                self.apify_client = ApifyClient(self.apify_token)
                logger.info(f"✅ Client Apify officiellement initialisé")
                self.initial_usage = self._get_current_usage()
            except Exception as e:
                logger.error(f"❌ Erreur initialisation client Apify: {e}")
                self.apify_client = None
                self.initial_usage = 0.0
        
        self.last_batch_start_usage = self.initial_usage
        
        logger.info(f"💰 Usage Apify initial: ${self.initial_usage:.4f}")
    
    def _load_tracking(self) -> dict:
        """Charger le fichier de tracking existant"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"💰 Session précédente: ${data.get('session_cost', 0):.4f}")
                    return data
            except Exception as e:
                logger.warning(f"⚠️ Impossible de charger les coûts: {e}")
        
        return {
            'start_time': datetime.now().isoformat(),
            'budget_limit': self.budget_limit,
            'session_cost': 0.0,  # Coût de cette session
            'initial_usage': 0.0,
            'clients': {},
            'batches': [],
            'warnings': []
        }
    
    def _save_tracking(self):
        """Sauvegarder le tracking"""
        self.data['last_update'] = datetime.now().isoformat()
        
        try:
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde coûts: {e}")
    
    def _get_current_usage(self) -> float:
        """
        Récupérer l'usage RÉEL depuis le compte Apify
        Utilise l'API Account pour obtenir le montant exact dépensé
        """
        try:
            if not self.apify_client:
                logger.debug("Client Apify non disponible")
                return 0.0
            
            # MÉTHODE 1 : Utiliser l'endpoint Account pour le montant total
            try:
                # Récupérer les infos du compte
                account_info = self.apify_client.account().get()
                
                if account_info:
                    # Le montant dépensé ce mois (en USD)
                    usage = account_info.get('usage', {})
                    
                    # Essayer différents champs selon la version API
                    current_month_usage = (
                        usage.get('currentMonthUsageUsd') or
                        usage.get('monthUsageUsd') or 
                        usage.get('usageUsd') or
                        0.0
                    )
                    
                    logger.debug(f"💰 Usage compte Apify: ${current_month_usage:.4f}")
                    return float(current_month_usage)
            except Exception as e:
                logger.debug(f"Impossible d'obtenir account info: {e}")
            
            # MÉTHODE 2 (FALLBACK) : Calculer depuis les runs
            logger.debug("Fallback: Calcul depuis les runs...")
            
            total_cost = 0.0
            run_count = 0
            
            # Récupérer les derniers 100 runs
            runs_page = self.apify_client.runs().list(limit=100)
            
            if runs_page and runs_page.items:
                for run_summary in runs_page.items:
                    run_id = run_summary.get('id')
                    
                    try:
                        # Récupérer les détails complets du run
                        full_run = self.apify_client.run(run_id).get()
                        
                        # Extraire le coût réel
                        usage_total_usd = full_run.get('usageTotalUsd')
                        
                        if usage_total_usd is not None:
                            # Utiliser directement usageTotalUsd si disponible
                            run_cost = float(usage_total_usd)
                        else:
                            # Sinon calculer depuis compute units
                            stats = full_run.get('stats', {})
                            compute_units = stats.get('computeUnits', 0.0)
                            
                            # Prix par compute unit (varie selon le plan Apify)
                            # Par défaut $0.25 par CU pour le plan gratuit
                            pricing_info = full_run.get('pricingInfo', {})
                            price_per_unit = pricing_info.get('pricePerUnitUsd', 0.25)
                            
                            run_cost = compute_units * price_per_unit
                        
                        if run_cost > 0:
                            total_cost += run_cost
                            run_count += 1
                            logger.debug(f"  Run {run_id}: ${run_cost:.4f}")
                    
                    except Exception as e:
                        logger.debug(f"  Skip run {run_id}: {e}")
                        continue
            
            logger.debug(f"Total: {run_count} runs = ${total_cost:.4f}")
            return total_cost
                
        except Exception as e:
            logger.error(f"Erreur calcul usage: {e}")
            return 0.0
    
    def get_session_cost(self) -> float:
        """Calculer le coût de cette session"""
        current_usage = self._get_current_usage()
        session_cost = current_usage - self.initial_usage
        return max(0, session_cost)  # Éviter les valeurs négatives
    
    def get_batch_cost(self) -> float:
        """Calculer le coût du batch en cours"""
        current_usage = self._get_current_usage()
        batch_cost = current_usage - self.last_batch_start_usage
        return max(0, batch_cost)
    
    def start_batch(self):
        """Marquer le début d'un nouveau batch"""
        self.last_batch_start_usage = self._get_current_usage()
    
    def record_client(self, client_id: str, metadata: dict = None):
        """
        Enregistrer un client traité (le coût sera calculé par batch)
        
        Args:
            client_id: ID du client
            metadata: Métadonnées du traitement
        """
        self.data['clients'][client_id] = {
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self._save_tracking()
    
    def end_batch(self, batch_number: int, clients_count: int):
        """Enregistrer la fin d'un batch avec le coût réel"""
        batch_cost = self.get_batch_cost()
        session_cost = self.get_session_cost()
        
        self.data['batches'].append({
            'batch_number': batch_number,
            'cost': batch_cost,
            'session_total': session_cost,
            'clients_count': clients_count,
            'avg_cost_per_client': batch_cost / clients_count if clients_count > 0 else 0,
            'timestamp': datetime.now().isoformat()
        })
        
        self.data['session_cost'] = session_cost
        
        # Vérifier le budget
        if self.is_budget_warning():
            warning = f"⚠️ Budget à {self.get_budget_percentage():.1f}%"
            logger.warning(warning)
            self.data['warnings'].append({
                'timestamp': datetime.now().isoformat(),
                'message': warning,
                'session_cost': session_cost
            })
        
        self._save_tracking()
        
        # Préparer le prochain batch
        self.start_batch()
    
    def is_budget_exceeded(self) -> bool:
        """Vérifier si le budget est dépassé"""
        return self.get_session_cost() >= self.budget_limit
    
    def is_budget_warning(self, threshold: float = 0.8) -> bool:
        """Vérifier si on approche du budget (80% par défaut)"""
        return self.get_session_cost() >= (self.budget_limit * threshold)
    
    def get_remaining_budget(self) -> float:
        """Obtenir le budget restant"""
        return max(0, self.budget_limit - self.get_session_cost())
    
    def get_budget_percentage(self) -> float:
        """Obtenir le pourcentage du budget utilisé"""
        return (self.get_session_cost() / self.budget_limit) * 100
    
    def estimate_remaining_clients(self) -> Optional[int]:
        """
        Estimer combien de clients peuvent encore être traités
        basé sur la moyenne réelle des derniers batches
        """
        if not self.data['batches']:
            return None
        
        # Calculer la moyenne des 3 derniers batches
        recent_batches = self.data['batches'][-3:]
        avg_costs = [b['avg_cost_per_client'] for b in recent_batches if b['clients_count'] > 0]
        
        if not avg_costs:
            return None
        
        avg_cost_per_client = sum(avg_costs) / len(avg_costs)
        remaining_budget = self.get_remaining_budget()
        
        if avg_cost_per_client > 0:
            return int(remaining_budget / avg_cost_per_client)
        return None
    
    def get_cost_report(self) -> dict:
        """Générer un rapport détaillé des coûts RÉELS"""
        session_cost = self.get_session_cost()
        clients_processed = len(self.data['clients'])
        avg_cost = session_cost / clients_processed if clients_processed > 0 else 0
        
        return {
            'session_cost': round(session_cost, 4),
            'budget_limit': self.budget_limit,
            'remaining_budget': round(self.get_remaining_budget(), 4),
            'budget_used_percentage': round(self.get_budget_percentage(), 2),
            'clients_processed': clients_processed,
            'average_cost_per_client': round(avg_cost, 4),
            'estimated_remaining_clients': self.estimate_remaining_clients(),
            'batches_completed': len(self.data['batches']),
            'warnings_count': len(self.data['warnings']),
            'current_apify_usage': round(self._get_current_usage(), 4)
        }
    
    def print_report(self):
        """Afficher un rapport des coûts avec visualisation améliorée"""
        report = self.get_cost_report()
        
        # Barre de progression du budget
        percentage = report['budget_used_percentage']
        bar_length = 40
        filled = int(bar_length * percentage / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        # Couleur selon le niveau d'alerte
        if percentage >= 90:
            status_icon = "🔴 CRITIQUE"
        elif percentage >= 80:
            status_icon = "🟠 ATTENTION"
        elif percentage >= 60:
            status_icon = "🟡 SURVEILLER"
        else:
            status_icon = "🟢 OK"
        
        print("\n" + "="*70)
        print("💰 RAPPORT DES COÛTS APIFY (TEMPS RÉEL)")
        print("="*70)
        print(f"\n📊 BUDGET: {status_icon}")
        print(f"   [{bar}] {percentage:.1f}%")
        print(f"   Utilisé: ${report['session_cost']:.4f} / ${report['budget_limit']:.2f}")
        print(f"   Restant: ${report['remaining_budget']:.4f}")
        
        print(f"\n👥 CLIENTS TRAITÉS:")
        print(f"   Total: {report['clients_processed']} clients")
        print(f"   Coût moyen: ${report['average_cost_per_client']:.4f} par client")
        
        if report['estimated_remaining_clients']:
            print(f"\n🎯 ESTIMATION:")
            print(f"   Clients restants possibles: ~{report['estimated_remaining_clients']} clients")
            print(f"   (basé sur la moyenne des derniers batches)")
        
        print(f"\n📦 BATCHES:")
        print(f"   Complétés: {report['batches_completed']}")
        
        # Afficher les derniers batches avec leurs coûts
        if self.data['batches']:
            print(f"\n📈 HISTORIQUE DES 3 DERNIERS BATCHES:")
            for batch in self.data['batches'][-3:]:
                print(f"   • Batch #{batch['batch_number']}: ${batch['cost']:.4f} "
                      f"({batch['clients_count']} clients, "
                      f"${batch['avg_cost_per_client']:.4f}/client)")
        
        print(f"\n💳 COMPTE APIFY:")
        print(f"   Usage total actuel: ${report['current_apify_usage']:.4f}")
        
        if report['warnings_count'] > 0:
            print(f"\n⚠️  {report['warnings_count']} alerte(s) budgétaire(s)")
        
        print("="*70 + "\n")
    
    def print_batch_cost(self, batch_number: int):
        """Afficher le coût d'un batch spécifique immédiatement après traitement"""
        batch_cost = self.get_batch_cost()
        session_cost = self.get_session_cost()
        remaining = self.get_remaining_budget()
        percentage = self.get_budget_percentage()
        
        # Indicateur visuel
        if percentage >= 90:
            icon = "🔴"
        elif percentage >= 80:
            icon = "🟠"
        elif percentage >= 60:
            icon = "🟡"
        else:
            icon = "🟢"
        
        print("\n" + "─"*70)
        print(f"💰 COÛT BATCH #{batch_number}")
        print("─"*70)
        print(f"   Batch: ${batch_cost:.4f}")
        print(f"   Session totale: ${session_cost:.4f} / ${self.budget_limit:.2f} {icon}")
        print(f"   Restant: ${remaining:.4f} ({100-percentage:.1f}%)")
        
        # Estimation
        estimated = self.estimate_remaining_clients()
        if estimated:
            print(f"   Estimation: ~{estimated} clients restants possibles")
        
        print("─"*70 + "\n")