"""
MetricsCalculator - Calcule tous les KPIs dynamiquement
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import Counter
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MetricsCalculator:
    """Calcule tous les indicateurs clés depuis les données MongoDB"""
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialiser avec les données chargées
        
        Args:
            data: Données retournées par DataLoader.get_all_data()
        """
        self.stores = data.get('stores', [])
        self.mappings = data.get('mappings', [])
        self.mappings_active = data.get('mappings_active', [])
        self.mappings_inactive = data.get('mappings_inactive', [])
        self.reports = data.get('reports', [])
        self.loaded_at = data.get('loaded_at', datetime.now())
    
    def get_overview_kpis(self) -> Dict[str, Any]:
        """
        Calculer les KPIs de vue d'ensemble
        
        IMPORTANT:
        - Actifs = clients avec type='report' (Phase 2) - données les plus récentes
        - Inactifs = clients avec status='inactive' ET type='mapping' (Phase 1)
        
        Returns:
            {
                'total_clients': 21764,
                'clients_traités': 718,
                'clients_restants': 21046,
                'progression': 3.3,
                'actifs': 40,
                'inactifs': 678,
                'ratio_actifs': 5.6
            }
        """
        total_clients = len(self.stores)
        traités = len(self.mappings)
        
        # Actifs = clients avec report Phase 2 (données les plus à jour)
        actifs = len(self.reports)
        
        # Inactifs = clients Phase 1 avec status='inactive' uniquement
        inactifs = len(self.mappings_inactive)
        
        kpis = {
            'total_clients': total_clients,
            'clients_traités': traités,
            'clients_restants': total_clients - traités,
            'progression': (traités / total_clients * 100) if total_clients > 0 else 0,
            'actifs': actifs,
            'inactifs': inactifs,
            'ratio_actifs': (actifs / traités * 100) if traités > 0 else 0,
            'ratio_inactifs': (inactifs / traités * 100) if traités > 0 else 0
        }
        
        logger.debug(f"KPIs calculés: {traités}/{total_clients} clients ({kpis['progression']:.1f}%)")
        return kpis
    
    def get_ads_kpis(self) -> Dict[str, Any]:
        """
        Calculer les KPIs publicités (depuis Phase 1 et Phase 2)
        
        Returns:
            {
                'total_ads': 1234,
                'converty_ads': 800,
                'competitor_ads': 434,
                'ratio_converty': 65.0
            }
        """
        # Si Phase 2 est disponible, utiliser UNIQUEMENT les rapports (données cohérentes)
        if self.reports:
            converty_ads = sum(r.get('metrics', {}).get('converty_ads', 0) for r in self.reports)
            competitor_ads = sum(r.get('metrics', {}).get('concurrent_ads', 0) for r in self.reports)
            total_ads = converty_ads + competitor_ads
        else:
            # Sinon utiliser Phase 1
            total_ads = sum(
                m.get('processing_metadata', {}).get('total_ads', 0) 
                for m in self.mappings
            )
            converty_ads = 0
            competitor_ads = 0
        
        total_classified = converty_ads + competitor_ads
        
        kpis = {
            'total_ads': total_ads,
            'converty_ads': converty_ads,
            'competitor_ads': competitor_ads,
            'ratio_converty': (converty_ads / total_classified * 100) if total_classified > 0 else 0,
            'has_phase2_data': len(self.reports) > 0
        }
        
        logger.debug(f"Ads KPIs: {total_ads} total, {converty_ads} Converty, {competitor_ads} Concurrent (Phase 2: {len(self.reports)} reports)")
        return kpis
    
    def get_top_competitors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Identifier les top concurrents depuis Phase 2
        
        Args:
            limit: Nombre de concurrents à retourner
        
        Returns:
            [
                {'domain': 'shopify.com', 'count': 45, 'platform': 'Shopify'},
                ...
            ]
        """
        if not self.reports:
            return []
        
        # Agréger tous les concurrents depuis la vraie structure
        all_competitors = []
        for report in self.reports:
            # Utiliser le champ competitors (pas classification)
            competitors = report.get('competitors', [])
            all_competitors.extend(competitors)
        
        # Compter par domaine
        competitor_counts = Counter()
        competitor_platforms = {}
        
        for comp in all_competitors:
            domain = comp.get('domain')
            if domain:
                competitor_counts[domain] += comp.get('total_ads', 1)
                competitor_platforms[domain] = comp.get('platform', 'Unknown')
        
        # Top N
        top = [
            {
                'domain': domain,
                'count': count,
                'platform': competitor_platforms.get(domain, 'Unknown')
            }
            for domain, count in competitor_counts.most_common(limit)
        ]
        
        logger.debug(f"Top {limit} concurrents calculés")
        return top
    
    def get_platform_distribution(self) -> Dict[str, int]:
        """
        Répartition des plateformes concurrentes
        
        Returns:
            {'Shopify': 45, 'WooCommerce': 30, 'Custom': 15, ...}
        """
        if not self.reports:
            return {}
        
        platform_counts = Counter()
        
        for report in self.reports:
            # Utiliser le champ competitors (pas classification)
            competitors = report.get('competitors', [])
            for comp in competitors:
                platform = comp.get('platform', 'Unknown')
                platform_counts[platform] += comp.get('total_ads', 1)
        
        return dict(platform_counts)
    
    def get_time_series_data(self, days: int = 30) -> Dict[str, List[Any]]:
        """
        Données pour graphiques temporels
        
        Args:
            days: Nombre de jours d'historique
        
        Returns:
            {
                'dates': [...],
                'nouveaux_clients': [...],
                'cumul_clients': [...]
            }
        """
        # Filtrer les mappings par date
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Grouper par jour
        daily_counts = Counter()
        for mapping in self.mappings:
            timestamp = mapping.get('timestamp')
            if timestamp:
                # Convertir si nécessaire
                if isinstance(timestamp, dict) and '$date' in timestamp:
                    date = datetime.fromisoformat(timestamp['$date'].replace('Z', '+00:00'))
                elif isinstance(timestamp, str):
                    date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    continue
                
                if date >= cutoff_date:
                    day_key = date.date()
                    daily_counts[day_key] += 1
        
        # Trier et créer séries
        sorted_days = sorted(daily_counts.keys())
        dates = sorted_days
        nouveaux = [daily_counts[day] for day in sorted_days]
        
        # Calcul cumulatif
        cumul = []
        total = 0
        for count in nouveaux:
            total += count
            cumul.append(total)
        
        return {
            'dates': dates,
            'nouveaux_clients': nouveaux,
            'cumul_clients': cumul
        }
    
    def get_activity_distribution(self) -> Dict[str, List[int]]:
        """
        Distribution des clients ACTIFS (Phase 2) par nombre de publicités
        
        IMPORTANT: Utilise uniquement Phase 2 car seuls les actifs ont des rapports
        
        Returns:
            {
                'bins': ['0-5', '5-10', '10-20', '20+'],
                'counts': [0, 5, 15, 20]  # nombre de clients actifs par catégorie
            }
        """
        # Utiliser UNIQUEMENT Phase 2 (actifs)
        if not self.reports:
            return {
                'bins': ['0-5', '5-10', '10-20', '20+'],
                'counts': [0, 0, 0, 0]
            }
        
        ads_counts = [
            report.get('metrics', {}).get('total_ads', 0)
            for report in self.reports
        ]
        
        # Créer les bins
        bins = {
            '0-5': 0,
            '5-10': 0,
            '10-20': 0,
            '20+': 0
        }
        
        for count in ads_counts:
            if count <= 5:
                bins['0-5'] += 1
            elif count <= 10:
                bins['5-10'] += 1
            elif count <= 20:
                bins['10-20'] += 1
            else:
                bins['20+'] += 1
        
        return {
            'bins': list(bins.keys()),
            'counts': list(bins.values())
        }
    
    def get_activity_distribution_inactive(self) -> Dict[str, List[int]]:
        """
        Distribution des clients INACTIFS (Phase 1) par nombre de publicités
        
        IMPORTANT: Utilise uniquement Phase 1 inactifs (status='inactive')
        
        Returns:
            {
                'bins': ['0-5', '5-10', '10-20', '20+'],
                'counts': [600, 50, 20, 8]
            }
        """
        # Utiliser UNIQUEMENT les inactifs
        if not self.mappings_inactive:
            return {
                'bins': ['0-5', '5-10', '10-20', '20+'],
                'counts': [0, 0, 0, 0]
            }
        
        ads_counts = [
            m.get('processing_metadata', {}).get('total_ads', 0)
            for m in self.mappings_inactive
        ]
        
        # Créer les bins
        bins = {
            '0-5': 0,
            '5-10': 0,
            '10-20': 0,
            '20+': 0
        }
        
        for count in ads_counts:
            if count <= 5:
                bins['0-5'] += 1
            elif count <= 10:
                bins['5-10'] += 1
            elif count <= 20:
                bins['10-20'] += 1
            else:
                bins['20+'] += 1
        
        return {
            'bins': list(bins.keys()),
            'counts': list(bins.values())
        }
    
    def get_client_table_data(self, 
                             status_filter: str = None,
                             search_query: str = None) -> List[Dict[str, Any]]:
        """
        Données pour la table interactive des clients
        
        Args:
            status_filter: 'active', 'inactive', ou None (tous)
            search_query: Recherche par client_id
        
        Returns:
            [
                {
                    'client_id': 'vervane',
                    'status': 'active',
                    'total_ads': 12,
                    'converty_pct': 75,
                    'top_competitor': 'shopify.com',
                    'last_activity': '2025-12-29'
                },
                ...
            ]
        """
        # Filtrer selon status
        if status_filter == 'active':
            mappings = self.mappings_active
        elif status_filter == 'inactive':
            mappings = self.mappings_inactive
        else:
            mappings = self.mappings
        
        # Construire les données table
        table_data = []
        
        for mapping in mappings:
            client_id = mapping.get('client_id')
            
            # Recherche
            if search_query and search_query.lower() not in client_id.lower():
                continue
            
            # Extraire métriques - PRIORISER Phase 2 si disponible
            status = mapping.get('status', 'unknown')
            timestamp = mapping.get('timestamp', {})
            
            # Trouver le rapport Phase 2 si existe
            report = next(
                (r for r in self.reports if r.get('client_id') == client_id),
                None
            )
            
            # Si Phase 2 existe, utiliser ses données (plus récentes)
            if report:
                metrics = report.get('metrics', {})
                total_ads = metrics.get('total_ads', 0)
                converty_pct = metrics.get('converty_ratio')  # Déjà en pourcentage
                
                competitors = report.get('competitors', [])
                top_competitor = competitors[0].get('domain') if competitors else 'N/A'
                
                # Utiliser le timestamp de Phase 2 (plus récent)
                timestamp = report.get('analyzed_at', timestamp)
            else:
                # Sinon, utiliser Phase 1
                total_ads = mapping.get('processing_metadata', {}).get('total_ads', 0)
                converty_pct = None
                top_competitor = 'N/A'
            
            # Dernière activité
            if isinstance(timestamp, dict) and '$date' in timestamp:
                last_activity = timestamp['$date'][:10]  # YYYY-MM-DD
            else:
                last_activity = 'N/A'
            
            table_data.append({
                'client_id': client_id,
                'status': status,
                'total_ads': total_ads,
                'converty_pct': converty_pct,
                'top_competitor': top_competitor or 'N/A',
                'last_activity': last_activity
            })
        
        logger.debug(f"Table data générée: {len(table_data)} clients")
        return table_data
