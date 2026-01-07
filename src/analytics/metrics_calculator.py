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

        # Prendre le DERNIER rapport par client (dernier analyzed_at)
        latest_reports = self._latest_report_per_client()

        # Actifs = clients dont le dernier rapport a des publicités (>0)
        actifs = sum(1 for r in latest_reports.values()
                 if r.get('metrics', {}).get('total_ads', 0) > 0)

        # Inactifs = (1) derniers rapports avec 0 ads + (2) mappings inactifs sans rapport
        inactive_from_reports = {cid for cid, r in latest_reports.items()
                     if r.get('metrics', {}).get('total_ads', 0) == 0}
        inactive_phase1_only = {m.get('client_id') for m in self.mappings_inactive
                     if m.get('client_id') not in latest_reports}
        inactifs = len(inactive_from_reports | inactive_phase1_only)
        
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
        Données pour graphiques temporels (Phase 1 mappings + Phase 2 reports)
        
        Args:
            days: Nombre de jours d'historique
        
        Returns:
            {
                'dates': [...],
                'nouveaux_clients': [...],
                'cumul_clients': [...],
                'nouveaux_reports': [...]
            }
        """
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Grouper mappings par jour
        daily_mappings = Counter()
        for mapping in self.mappings:
            timestamp = mapping.get('timestamp') or mapping.get('created_at')
            if timestamp:
                try:
                    if isinstance(timestamp, dict) and '$date' in timestamp:
                        date = datetime.fromisoformat(timestamp['$date'].replace('Z', '+00:00'))
                    elif isinstance(timestamp, str):
                        date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    elif hasattr(timestamp, 'date'):
                        date = timestamp
                    else:
                        continue
                    
                    if date >= cutoff_date:
                        day_key = date.date()
                        daily_mappings[day_key] += 1
                except Exception:
                    continue
        
        # Grouper reports Phase 2 par jour
        daily_reports = Counter()
        for report in self.reports:
            timestamp = report.get('analyzed_at') or report.get('timestamp')
            if timestamp:
                try:
                    if isinstance(timestamp, dict) and '$date' in timestamp:
                        date = datetime.fromisoformat(timestamp['$date'].replace('Z', '+00:00'))
                    elif isinstance(timestamp, str):
                        date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    elif hasattr(timestamp, 'date'):
                        date = timestamp
                    else:
                        continue
                    
                    if date >= cutoff_date:
                        day_key = date.date()
                        daily_reports[day_key] += 1
                except Exception:
                    continue
        
        # Fusionner toutes les dates
        all_dates = sorted(set(daily_mappings.keys()) | set(daily_reports.keys()))
        
        # Si aucune donnée, retourner structure vide mais valide
        if not all_dates:
            return {
                'dates': [],
                'nouveaux_clients': [],
                'cumul_clients': [],
                'nouveaux_reports': []
            }
        
        nouveaux_mappings = [daily_mappings.get(day, 0) for day in all_dates]
        nouveaux_reports = [daily_reports.get(day, 0) for day in all_dates]
        
        # Calcul cumulatif
        cumul = []
        total = 0
        for count in nouveaux_mappings:
            total += count
            cumul.append(total)
        
        return {
            'dates': all_dates,
            'nouveaux_clients': nouveaux_mappings,
            'cumul_clients': cumul,
            'nouveaux_reports': nouveaux_reports
        }

    def get_status_time_series(self, days: int = 30) -> Dict[str, List[int]]:
        """
        Évolution des statuts via Phase 2:
        - Nombre de rapports actifs/inactifs par jour
        - Nombre de clients actifs/inactifs cumulés (selon dernier état à la date)

        Returns:
            {
                'dates': [...],
                'active_reports': [...],
                'inactive_reports': [...],
                'active_clients_cumulative': [...],
                'inactive_clients_cumulative': [...]
            }
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Préparer liste des rapports avec date et statut
        def parse_dt(val):
            if not val:
                return None
            try:
                if isinstance(val, dict) and '$date' in val:
                    return datetime.fromisoformat(val['$date'].replace('Z', '+00:00'))
                elif isinstance(val, str):
                    return datetime.fromisoformat(val.replace('Z', '+00:00'))
            except Exception:
                return None
            return None

        reports = []
        for r in self.reports:
            dt = parse_dt(r.get('analyzed_at') or r.get('timestamp'))
            if not dt:
                continue
            if dt < cutoff_date:
                continue
            client_id = r.get('client_id') or r.get('client_slug')
            if not client_id:
                continue
            total_ads = r.get('metrics', {}).get('total_ads', 0)
            is_active = total_ads > 0
            reports.append({'date': dt.date(), 'client_id': client_id, 'active': is_active, 'dt': dt})

        if not reports:
            return {
                'dates': [],
                'active_reports': [],
                'inactive_reports': [],
                'active_clients_cumulative': [],
                'inactive_clients_cumulative': []
            }

        # Groupes par jour pour counts de rapports
        daily_active = Counter()
        daily_inactive = Counter()
        for rec in reports:
            if rec['active']:
                daily_active[rec['date']] += 1
            else:
                daily_inactive[rec['date']] += 1

        # Dates ordonnées
        all_dates = sorted(set([rec['date'] for rec in reports]))

        # Cumul des statuts clients au fil du temps
        # On applique les rapports jour par jour et on calcule le statut courant (dernier état)
        status_by_client = {}
        active_cum = []
        inactive_cum = []

        # Pour éviter des doubles mises à jour par jour, on prend le dernier report par client pour chaque jour
        from collections import defaultdict
        reports_by_day_client = defaultdict(dict)  # day -> client -> last active
        for rec in sorted(reports, key=lambda x: x['dt']):
            reports_by_day_client[rec['date']][rec['client_id']] = rec['active']

        for day in all_dates:
            for cid, active in reports_by_day_client[day].items():
                status_by_client[cid] = active
            active_count = sum(1 for v in status_by_client.values() if v)
            inactive_count = len(status_by_client) - active_count
            active_cum.append(active_count)
            inactive_cum.append(inactive_count)

        return {
            'dates': all_dates,
            'active_reports': [daily_active.get(d, 0) for d in all_dates],
            'inactive_reports': [daily_inactive.get(d, 0) for d in all_dates],
            'active_clients_cumulative': active_cum,
            'inactive_clients_cumulative': inactive_cum
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
        # Utiliser UNIQUEMENT les derniers rapports actifs (total_ads > 0)
        latest_reports = self._latest_report_per_client()
        if not latest_reports:
            return {
                'bins': ['0-5', '5-10', '10-20', '20+'],
                'counts': [0, 0, 0, 0]
            }
        
        ads_counts = [
            r.get('metrics', {}).get('total_ads', 0)
            for r in latest_reports.values()
            if r.get('metrics', {}).get('total_ads', 0) > 0
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

    def _latest_report_per_client(self) -> Dict[str, Dict[str, Any]]:
        """Retourner le dernier rapport (Phase 2) pour chaque client.
        Gère analyzed_at au format dict {'$date': ...} ou str.
        """
        latest: Dict[str, Dict[str, Any]] = {}
        def parse_dt(val):
            if not val:
                return datetime.min
            try:
                if isinstance(val, dict) and '$date' in val:
                    s = val['$date']
                    # Support '...Z' suffix
                    return datetime.fromisoformat(s.replace('Z', '+00:00'))
                if isinstance(val, str):
                    return datetime.fromisoformat(val.replace('Z', '+00:00'))
            except Exception:
                return datetime.min
            return datetime.min
        for r in self.reports:
            cid = r.get('client_id') or r.get('client_slug')
            if not cid:
                continue
            dt = parse_dt(r.get('analyzed_at') or r.get('timestamp'))
            prev = latest.get(cid)
            if not prev:
                latest[cid] = r
            else:
                prev_dt = parse_dt(prev.get('analyzed_at') or prev.get('timestamp'))
                if dt >= prev_dt:
                    latest[cid] = r
        return latest
    
    
    def get_client_execution_history(self, client_id: str) -> List[Dict[str, Any]]:
        """
        Historique des exécutions pour un client spécifique
        
        Args:
            client_id: ID du client
        
        Returns:
            Liste des exécutions avec timestamps et métriques
        """
        history = []
        
        # Phase 1 mappings
        for mapping in self.mappings:
            if mapping.get('client_id') == client_id:
                history.append({
                    'date': mapping.get('timestamp') or mapping.get('created_at'),
                    'phase': 'Phase 1',
                    'type': 'mapping',
                    'status': mapping.get('status'),
                    'total_ads': mapping.get('processing_metadata', {}).get('total_ads', 0)
                })
        
        # Phase 2 reports
        for report in self.reports:
            if report.get('client_id') == client_id:
                metrics = report.get('metrics', {})
                history.append({
                    'date': report.get('analyzed_at') or report.get('timestamp'),
                    'phase': 'Phase 2',
                    'type': 'report',
                    'total_ads': metrics.get('total_ads', 0),
                    'converty_ads': metrics.get('converty_ads', 0),
                    'concurrent_ads': metrics.get('concurrent_ads', 0),
                    'converty_ratio': metrics.get('converty_ratio', 0)
                })
        
        # Trier par date décroissante
        history.sort(key=lambda x: x['date'] if x['date'] else datetime.min, reverse=True)
        return history
    
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
        # Construire la vue "par client" basée sur le DERNIER rapport
        latest_reports = self._latest_report_per_client()
        exec_counts = Counter(r.get('client_id') or r.get('client_slug') for r in self.reports)

        # Ensemble de tous les clients (dernier rapport ou mapping inactive)
        all_client_ids = set(latest_reports.keys()) | {m.get('client_id') for m in self.mappings_inactive}

        # Construire les données table
        table_data = []
        for client_id in sorted(all_client_ids):
            if not client_id:
                continue
            # Recherche
            if search_query and search_query.lower() not in client_id.lower():
                continue

            latest = latest_reports.get(client_id)
            # Déterminer statut actuel
            if latest:
                metrics = latest.get('metrics', {})
                total_ads = metrics.get('total_ads', 0)
                status = 'active' if total_ads > 0 else 'inactive'
                timestamp = latest.get('analyzed_at') or latest.get('timestamp')
                converty_pct = metrics.get('converty_ratio')
                competitors = latest.get('competitors', [])
                top_competitor = competitors[0].get('domain') if competitors else 'N/A'
            else:
                # Aucun rapport Phase 2 → utiliser mapping Phase 1
                mapping = next((m for m in self.mappings_inactive if m.get('client_id') == client_id), None)
                status = mapping.get('status', 'inactive') if mapping else 'inactive'
                total_ads = mapping.get('processing_metadata', {}).get('total_ads', 0) if mapping else 0
                timestamp = mapping.get('timestamp') if mapping else None
                converty_pct = None
                top_competitor = 'N/A'

            # Dernière activité formatée
            if isinstance(timestamp, dict) and '$date' in timestamp:
                last_activity = timestamp['$date'][:19]
            elif isinstance(timestamp, str):
                last_activity = timestamp[:19]
            else:
                last_activity = 'N/A'

            table_data.append({
                'client_id': client_id,
                'status': status,
                'total_ads': total_ads,
                'converty_pct': converty_pct,
                'top_competitor': top_competitor or 'N/A',
                'last_activity': last_activity,
                'executions': exec_counts.get(client_id, 0)
            })

        # Appliquer filtre de statut après construction
        if status_filter in {'active', 'inactive'}:
            table_data = [row for row in table_data if row['status'] == status_filter]
        
        logger.debug(f"Table data générée: {len(table_data)} clients")
        return table_data
