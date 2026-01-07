"""
Dashboard Streamlit - Converty Analytics
Application interactive pour le suivi des clients et concurrents
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.analytics.data_loader import DataLoader
from src.analytics.metrics_calculator import MetricsCalculator
from src.analytics.charts import ChartGenerator

# Configuration de la page
st.set_page_config(
    page_title="Converty Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #10b981;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .status-active {
        color: #22c55e;
        font-weight: bold;
    }
    .status-inactive {
        color: #6b7280;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=15)
def load_all_data(refresh_key: int):
    """Charger toutes les données depuis MongoDB (avec cache)"""
    loader = DataLoader()
    data = loader.get_all_data()
    loader.close()
    return data


def main():
    """Application principale"""
    
    # ==================== HEADER ====================
    st.markdown('<h1 class="main-header">📊 Converty Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Gestion clé de rafraîchissement (casse le cache au clic)
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    if 'refresh_key' not in st.session_state:
        st.session_state.refresh_key = int(st.session_state.last_refresh.timestamp())
    
    col_refresh1, col_refresh2, col_refresh3 = st.columns([2, 1, 1])
    with col_refresh1:
        st.caption(f"🕒 Dernière mise à jour: {st.session_state.last_refresh.strftime('%d/%m/%Y %H:%M:%S')}")
    with col_refresh2:
        if st.button("🔄 Rafraîchir", use_container_width=True):
            # Buster le cache en changeant une clé d'argument
            st.session_state.last_refresh = datetime.now()
            st.session_state.refresh_key = int(st.session_state.last_refresh.timestamp())
            st.rerun()
    with col_refresh3:
        auto_refresh = st.checkbox("Auto-refresh 30s", value=False)
    
    st.divider()
    
    # ==================== CHARGEMENT DONNÉES ====================
    with st.spinner("📥 Chargement des données MongoDB..."):
        data = load_all_data(st.session_state.refresh_key)
        
    # Afficher métriques de chargement pour vérifier la fraîcheur
    st.caption(
        f"📦 Données: stores={len(data.get('stores', []))}, "
        f"mappings={len(data.get('mappings', []))}, "
        f"reports={len(data.get('reports', []))} · "
        f"chargées à {data.get('loaded_at').strftime('%d/%m/%Y %H:%M:%S')}"
    )
    
    # Initialiser calculateur et générateur de charts
    calc = MetricsCalculator(data)
    charts = ChartGenerator()
    
    # ==================== SIDEBAR - FILTRES ====================
    st.sidebar.header("🎛️ Filtres & Navigation")
    
    # Filtre période
    st.sidebar.subheader("📅 Période")
    period = st.sidebar.selectbox(
        "Historique",
        ["7 derniers jours", "30 derniers jours", "90 derniers jours", "Tout l'historique"],
        index=1
    )
    period_days = {
        "7 derniers jours": 7,
        "30 derniers jours": 30,
        "90 derniers jours": 90,
        "Tout l'historique": 365
    }[period]
    
    # Filtre statut
    st.sidebar.subheader("🔍 Statut clients")
    status_filter = st.sidebar.radio(
        "Afficher",
        ["Tous", "Actifs uniquement", "Inactifs uniquement"],
        index=0
    )
    
    # Filtre seuil ads
    st.sidebar.subheader("📊 Seuil d'activité")
    min_ads = st.sidebar.slider("Minimum de publicités", 0, 50, 5)
    
    # Recherche client
    st.sidebar.subheader("🔎 Recherche")
    search_query = st.sidebar.text_input("ID Client", placeholder="Ex: vervane")
    
    st.sidebar.divider()
    
    # Navigation
    st.sidebar.header("📍 Navigation")
    page = st.sidebar.radio(
        "Sections",
        ["Vue d'ensemble", "Analyse temporelle", "Concurrence", "Détails clients", "Alertes"],
        index=0
    )
    
    # ==================== SECTION 1: VUE D'ENSEMBLE ====================
    if page == "Vue d'ensemble":
        st.header("📊 Vue d'ensemble")
        
        # KPIs principaux
        overview_kpis = calc.get_overview_kpis()
        ads_kpis = calc.get_ads_kpis()
        
        # Progress bar globale
        st.subheader("Progression du traitement")
        st.progress(overview_kpis['progression'] / 100)
        st.caption(f"**{overview_kpis['clients_traités']:,} / {overview_kpis['total_clients']:,} clients traités** ({overview_kpis['progression']:.1f}%)")
        
        st.divider()
        
        # Métriques en colonnes
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📦 Total Clients",
                value=f"{overview_kpis['total_clients']:,}",
                delta=f"{overview_kpis['clients_restants']:,} restants"
            )
        
        with col2:
            st.metric(
                label="🟢 Clients Actifs",
                value=f"{overview_kpis['actifs']:,}",
                delta=f"{overview_kpis['ratio_actifs']:.1f}%"
            )
        
        with col3:
            st.metric(
                label="🔴 Clients Inactifs",
                value=f"{overview_kpis['inactifs']:,}",
                delta=f"{overview_kpis['ratio_inactifs']:.1f}%"
            )
        
        with col4:
            st.metric(
                label="📊 Total Publicités",
                value=f"{ads_kpis['total_ads']:,}",
                delta="Depuis Phase 1"
            )
        
        st.divider()
        
        # Row 2
        col5, col6, col7 = st.columns(3)
        
        with col5:
            if ads_kpis['has_phase2_data']:
                st.metric(
                    label="✅ Publicités Converty",
                    value=f"{ads_kpis['converty_ads']:,}",
                    delta=f"{ads_kpis['ratio_converty']:.1f}%"
                )
            else:
                st.info("ℹ️ Phase 2 non complétée - Pas de données de classification")
        
        with col6:
            if ads_kpis['has_phase2_data']:
                st.metric(
                    label="⚠️ Publicités Concurrents",
                    value=f"{ads_kpis['competitor_ads']:,}",
                    delta=f"{100 - ads_kpis['ratio_converty']:.1f}%"
                )
        
        with col7:
            st.metric(
                label="📈 Ratio Converty",
                value=f"{ads_kpis['ratio_converty']:.1f}%" if ads_kpis['has_phase2_data'] else "N/A",
                delta="Objectif: >70%"
            )
        
        st.divider()
        
        # Graphiques côte à côte
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("Répartition Actifs/Inactifs")
            pie_fig = charts.create_pie_chart(
                labels=['Actifs', 'Inactifs'],
                values=[overview_kpis['actifs'], overview_kpis['inactifs']],
                title="Statut des clients traités"
            )
            st.plotly_chart(pie_fig, use_container_width=True)
        
        with chart_col2:
            st.subheader("Distribution Clients ACTIFS (Phase 2)")
            dist_data_active = calc.get_activity_distribution()
            bar_fig_active = charts.create_bar_chart(
                labels=dist_data_active['bins'],
                values=dist_data_active['counts'],
                title=f"Clients Actifs: {sum(dist_data_active['counts'])} clients",
                horizontal=False
            )
            st.plotly_chart(bar_fig_active, use_container_width=True)
        
        # Deuxième ligne pour les inactifs
        st.divider()
        st.subheader("📊 Distribution Clients INACTIFS (Phase 1)")
        
        col_inactive1, col_inactive2 = st.columns(2)
        
        with col_inactive1:
            dist_data_inactive = calc.get_activity_distribution_inactive()
            bar_fig_inactive = charts.create_bar_chart(
                labels=dist_data_inactive['bins'],
                values=dist_data_inactive['counts'],
                title=f"Clients Inactifs: {sum(dist_data_inactive['counts'])} clients",
                horizontal=False
            )
            st.plotly_chart(bar_fig_inactive, use_container_width=True)
        
        with col_inactive2:
            st.info("""
            **📌 Explication:**
            - **Actifs (Phase 2)** : Clients avec des publicités détectées lors du dernier scan
            - **Inactifs (Phase 1)** : Clients sans publicités lors de la Phase 1 initiale
            
            ⚠️ Un client peut passer de "Actif" à "Inactif" entre deux runs si ses publicités sont supprimées
            """)
    
    # ==================== SECTION 2: ANALYSE TEMPORELLE ====================
    elif page == "Analyse temporelle":
        st.header("📈 Analyse temporelle")
        
        time_data = calc.get_time_series_data(days=period_days)
        status_ts = calc.get_status_time_series(days=period_days)
        
        if time_data['dates']:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("📊 Période analysée", f"{len(time_data['dates'])} jours")
            with col2:
                st.metric("🆕 Total traité", sum(time_data['nouveaux_clients']))
            
            st.divider()
            
            st.subheader("Évolution du traitement")
            area_fig = charts.create_area_chart(
                dates=time_data['dates'],
                values=time_data['cumul_clients'],
                label="Clients traités (cumulé)"
            )
            st.plotly_chart(area_fig, use_container_width=True)
            
            st.divider()
            
            st.subheader("Nouveaux clients traités par jour")
            line_fig = charts.create_time_series(
                dates=time_data['dates'],
                values_dict={
                    'Phase 1 (Discovery)': time_data['nouveaux_clients'],
                    'Phase 2 (Classification)': time_data.get('nouveaux_reports', [])
                }
            )
            st.plotly_chart(line_fig, use_container_width=True)

            st.divider()

            # Statut des rapports par jour (Phase 2)
            if status_ts['dates']:
                st.subheader("Statut des rapports par jour (Phase 2)")
                status_fig = charts.create_time_series(
                    dates=status_ts['dates'],
                    values_dict={
                        'Rapports actifs': status_ts['active_reports'],
                        'Rapports inactifs': status_ts['inactive_reports']
                    }
                )
                st.plotly_chart(status_fig, use_container_width=True)

                st.subheader("Clients actifs cumulés (dernier état au fil du temps)")
                active_cum_fig = charts.create_time_series(
                    dates=status_ts['dates'],
                    values_dict={
                        'Clients actifs (cumul)': status_ts['active_clients_cumulative'],
                        'Clients inactifs (cumul)': status_ts['inactive_clients_cumulative']
                    }
                )
                st.plotly_chart(active_cum_fig, use_container_width=True)
        else:
            st.info("ℹ️ Aucune donnée temporelle pour la période sélectionnée. Essayez 'Tout l'historique' dans les filtres.")
    
    # ==================== SECTION 3: CONCURRENCE ====================
    elif page == "Concurrence":
        st.header("🎯 Analyse concurrentielle")
        
        ads_kpis = calc.get_ads_kpis()
        
        if not ads_kpis['has_phase2_data']:
            st.warning("⚠️ Phase 2 non complétée - Lancez Phase 2 pour voir l'analyse concurrentielle")
            st.code("python phase2_main.py", language="bash")
        else:
            # Afficher la date de dernière analyse
            if data['reports']:
                latest_report = max(data['reports'], key=lambda r: r.get('analyzed_at', ''))
                latest_date = latest_report.get('analyzed_at', 'N/A')
                if isinstance(latest_date, dict) and '$date' in latest_date:
                    latest_date = latest_date['$date'][:19]
                st.caption(f"📅 Dernière analyse Phase 2: {latest_date}")
            
            st.divider()
            
            # Top concurrents
            st.subheader("Top 10 Concurrents")
            top_competitors = calc.get_top_competitors(limit=10)
            
            if top_competitors:
                comp_df = pd.DataFrame(top_competitors)
                
                # Bar chart horizontal
                comp_fig = charts.create_bar_chart(
                    labels=comp_df['domain'].tolist(),
                    values=comp_df['count'].tolist(),
                    title="Nombre de publicités par concurrent",
                    horizontal=True
                )
                st.plotly_chart(comp_fig, use_container_width=True)
                
                st.divider()
                
                # Répartition plateformes
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Répartition par plateforme")
                    platform_dist = calc.get_platform_distribution()
                    if platform_dist:
                        platform_fig = charts.create_pie_chart(
                            labels=list(platform_dist.keys()),
                            values=list(platform_dist.values()),
                            title="Plateformes concurrentes"
                        )
                        st.plotly_chart(platform_fig, use_container_width=True)
                
                with col2:
                    st.subheader("Table des concurrents")
                    st.dataframe(
                        comp_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "domain": "Domaine",
                            "count": st.column_config.NumberColumn("Publicités", format="%d"),
                            "platform": "Plateforme"
                        }
                    )
            else:
                st.info("Aucun concurrent identifié pour le moment")
    
    # ==================== SECTION 4: DÉTAILS CLIENTS ====================
    elif page == "Détails clients":
        st.header("📋 Détails par client")
        
        # Appliquer filtres
        status_map = {
            "Tous": None,
            "Actifs uniquement": "active",
            "Inactifs uniquement": "inactive"
        }
        
        table_data = calc.get_client_table_data(
            status_filter=status_map[status_filter],
            search_query=search_query if search_query else None
        )
        
        if table_data:
            df = pd.DataFrame(table_data)
            
            # Filtrer par min_ads
            df = df[df['total_ads'] >= min_ads]
            
            st.caption(f"**{len(df)} clients** correspondent aux filtres")
            
            # Ajout : historique d'exécution par client
            with st.expander("🔍 Voir l'historique d'exécution d'un client"):
                client_ids = df['client_id'].tolist()
                if client_ids:
                    selected_client = st.selectbox("Sélectionnez un client", client_ids)
                    
                    if selected_client:
                        history = calc.get_client_execution_history(selected_client)
                        
                        if history:
                            st.subheader(f"Historique pour {selected_client}")
                            
                            # Convertir en DataFrame pour affichage
                            history_df = pd.DataFrame(history)
                            
                            # Formater les dates
                            def format_date(date_val):
                                if isinstance(date_val, dict) and '$date' in date_val:
                                    return date_val['$date'][:19]
                                elif isinstance(date_val, str):
                                    return date_val[:19]
                                return str(date_val)
                            
                            history_df['date'] = history_df['date'].apply(format_date)
                            
                            st.dataframe(
                                history_df,
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("Aucun historique trouvé pour ce client")
            
            st.divider()
            
            # Table interactive
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "client_id": "Client ID",
                    "status": st.column_config.TextColumn(
                        "Statut",
                        help="Statut du client"
                    ),
                    "total_ads": st.column_config.NumberColumn(
                        "Total Ads",
                        format="%d"
                    ),
                    "converty_pct": st.column_config.NumberColumn(
                        "Converty %",
                        format="%.1f%%"
                    ),
                    "top_competitor": "Top Concurrent",
                    "last_activity": "Dernière activité"
                },
                height=600
            )
            
            # Export CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Télécharger CSV",
                data=csv,
                file_name=f"converty_clients_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("Aucun client ne correspond aux filtres")
    
    # ==================== SECTION 5: ALERTES ====================
    elif page == "Alertes":
        st.header("⚠️ Alertes & Recommandations")
        
        overview_kpis = calc.get_overview_kpis()
        ads_kpis = calc.get_ads_kpis()
        
        # Alertes critiques
        st.subheader("🚨 Alertes critiques")
        
        alert_col1, alert_col2 = st.columns(2)
        
        with alert_col1:
            if overview_kpis['ratio_actifs'] < 10:
                st.error(f"⚠️ Seulement {overview_kpis['ratio_actifs']:.1f}% de clients actifs !")
            else:
                st.success(f"✅ {overview_kpis['ratio_actifs']:.1f}% de clients actifs")
        
        with alert_col2:
            if ads_kpis['has_phase2_data'] and ads_kpis['ratio_converty'] < 50:
                st.error(f"⚠️ Ratio Converty faible : {ads_kpis['ratio_converty']:.1f}%")
            elif ads_kpis['has_phase2_data']:
                st.success(f"✅ Bon ratio Converty : {ads_kpis['ratio_converty']:.1f}%")
        
        st.divider()
        
        # Recommandations
        st.subheader("💡 Recommandations")
        
        reco1, reco2, reco3 = st.columns(3)
        
        with reco1:
            st.info(f"📊 **{overview_kpis['clients_restants']:,} clients restants**\n\nContinuer Phase 1 pour compléter le mapping")
        
        with reco2:
            if not ads_kpis['has_phase2_data']:
                st.warning("⚠️ **Phase 2 non lancée**\n\nLancer la classification des concurrents")
            else:
                st.success("✅ **Phase 2 complétée**\n\nDonnées de concurrence disponibles")
        
        with reco3:
            inactive_count = overview_kpis['inactifs']
            st.warning(f"🔴 **{inactive_count} clients inactifs**\n\nVérification manuelle recommandée")
    
    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
