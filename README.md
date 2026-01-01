# 📊 Sellers Ads Metrics - Intelligence Marketing Meta Ads

## 🎯 Vue d'ensemble

Système d'analyse automatisé pour monitorer et classifier les publicités Meta (Facebook) de **21,764 clients e-commerce**. Le projet identifie les clients actifs, analyse leurs stratégies publicitaires et détecte la concurrence via un pipeline en deux phases + dashboard interactif.

---

## ✨ Fonctionnalités principales

### 📍 Phase 1 : Discovery & Mapping
- **Scraping automatisé** via Apify Meta Ad Library Actor
- **Classification activité** : Actifs (avec publicités) vs Inactifs (sans publicités)
- **Tracking des coûts** en temps réel (budget $5 Apify)
- **Résultat** : 718 clients traités → 40 actifs (5.6%) + 678 inactifs (94.4%)

### 🎯 Phase 2 : Classification Intelligence
- **Analyse sémantique** des URLs de destination des publicités
- **Classification multi-catégories** :
  - ✅ **Converty Ads** : Publicités pointant vers domaines Converty
  - 🎯 **Concurrent Ads** : Publicités pointant vers concurrents identifiés
  - ❓ **Unknown Ads** : Publicités non classifiées
- **Détection concurrence** : Identification automatique des plateformes concurrentes
- **Métriques calculées** : Ratios Converty vs Concurrent par client

### 📊 Dashboard Streamlit
Interface interactive avec 5 sections analytiques :

1. **📈 Vue d'ensemble** : KPIs clés (clients traités, taux d'activité, volume publicités)
2. **⏱️ Analyse temporelle** : Évolution quotidienne et cumulative du traitement
3. **🏆 Analyse concurrentielle** : Top concurrents, distribution des plateformes
4. **🔍 Détails clients** : Table interactive avec recherche et filtres
5. **⚠️ Alertes & Recommandations** : Insights automatiques

---

## 🚀 Démarrage Rapide

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

```bash
# .env
APIFY_API_TOKEN=your_token_here
MONGODB_URI=mongodb://localhost:27017
```

**Phase 2 : Classification**
```bash
python phase2_main.py
```

**Dashboard Interactif**
```bash
streamlit run dashboard.py
```

---

## 🏗️ Architecture

```
sellers-ads-metrics/
├── phase1_main.py              # Pipeline Phase 1 (Discovery)
├── phase2_main.py              # Pipeline Phase 2 (Classification)
├── dashboard.py                # Dashboard Streamlit interactif
│
├── config/
│   └── settings.py             # Configuration centralisée
│
├── src/
│   ├── discovery/              # Phase 1: Scraping & Mapping
│   │   ├── apify_client.py
│   │   ├── mapper.py
│   │   └── cost_tracker.py
│   ├── classification/         # Phase 2: Analyse & Classification
│   │   ├── analyzer.py
│   │   └── detector.py
│   ├── analytics/              # Dashboard: Métriques & Visualisations
│   │   ├── data_loader.py
│   │   ├── metrics_calculator.py
│   │   └── charts.py
│   ├── database/               # MongoDB Integration
│   │   └── mongodb_client.py
│   └── utils/                  # Utilitaires partagés
│       └── logger.py
│
├── scripts/
│   ├── check_mongodb.py
│   ├── view_costs.py
│   └── report_inactive_clients.py
│
└── data/
    └── cache/
```

---

## 📊 Résultats Clés

### 🔍 Phase 1 - Discovery (718 clients analysés)

| Métrique | Valeur | Détail |
|----------|--------|--------|
| **Clients totaux** | 21,764 | Base MongoDB `stores` |
| **Clients traités** | 718 | 3.3% (limité budget Apify $5) |
| **Clients actifs** | 40 | 5.6% ont des publicités |
| **Clients inactifs** | 678 | 94.4% sans publicités |
| **Publicités totales** | 1,317 | Découvertes dans Meta Ads Library |
| **Budget consommé** | $5.00 | Limite Apify mensuelle |

### 🎯 Phase 2 - Classification (40 clients actifs)

| Métrique | Valeur | Ratio |
|----------|--------|-------|
| **Publicités classifiées** | 1,366 | 100% |
| **Converty Ads** | 1,354 | 99.1% |
| **Concurrent Ads** | 12 | 0.9% |
| **Unknown Ads** | 0 | 0% |
| **Concurrents uniques** | 3 | WhatsApp API, autres |

---

## 📊 Structure des Données

### MongoDB - Collection `ads_metrics`

**Phase 1 - Documents Mapping** (`type='mapping'`)
```json
{
  "client_id": "vervane",
  "type": "mapping",
  "status": "active",
  "domain": "vervane.converty.shop",
  "processing_metadata": {
    "total_ads": 12,
    "facebook_pages": ["110379551822943"],
    "scraping_cost": 0.007
  },
  "sites_mapping": {
    "vervane.converty.shop": {
      "facebook_pages": ["110379551822943"],
      "total_ads": 12
    }
  },
  "timestamp": "2025-12-29T16:30:00.000Z"
}
```

**Phase 2 - Documents Report** (`type='report'`)
```json
{
  "client_id": "vervane",
  "type": "report",
  "domain": "vervane.converty.shop",
  "metrics": {
    "total_ads": 94,
    "converty_ads": 94,
    "concurrent_ads": 0,
    "unknown_ads": 0,
    "converty_ratio": 100.0,
    "concurrent_ratio": 0.0
  },
  "facebook_pages": [
    {
      "page_id": "110379551822943",
      "page_name": "Vervane Store",
      "total_ads": 94,
      "converty_ads": 94,
      "concurrent_ads": 0,
      "converty_ratio": 100
    }
  ],
  "competitors": [],
  "analyzed_at": "2025-12-29T17:45:00.000Z"
}
```

---

## 🎨 Dashboard - Sections

### 1️⃣ Vue d'ensemble
**KPIs principaux**
- Total clients : 21,764
- Clients traités : 718 (3.3%)
- Clients actifs : 40 (5.6%)
- Publicités Converty : 1,354 (99.1%)
- Publicités Concurrents : 12 (0.9%)

**Graphiques**
- Jauge de progression (718/21,764)
- Ratio actifs/inactifs (pie chart)

### 2️⃣ Analyse Temporelle
- Évolution cumulative des clients traités
- Nouveaux clients par jour
- Filtres : 7/30/90 jours ou historique complet

### 3️⃣ Analyse Concurrentielle
- Top 10 concurrents (bar chart)
- Distribution des plateformes (pie chart)
- Détection automatique des URL concurrentes

### 4️⃣ Détails Clients
**Table interactive avec :**
- Client ID, Status, Total ads
- % Converty, Top concurrent
- Dernière activité

**Fonctionnalités :**
- 🔍 Recherche par client_id
- 📊 Filtres status (actif/inactif)
- 📥 Export CSV
- 🔄 Auto-refresh (60s)

### 5️⃣ Alertes & Recommandations
- Alertes critiques (clients à fort volume concurrent)
- Recommandations stratégiques
- Tendances détectées

---

## 💡 Insights & Stratégie

### 📈 Analyse des Résultats

**✅ Points forts**
- **99.1% Converty Ads** → Forte adoption de la plateforme Converty
- **5.6% taux d'activité** → Opportunité de réactivation pour les 94.4% inactifs
- **Concurrence faible** → Position dominante avec seulement 0.9% de concurrent ads

**⚠️ Points d'attention**
- **3.3% clients traités** → 96.7% restent à analyser (21,046 clients)
- **Budget limité** → Nécessite upgrade Apify ou attente reset mensuel
- **Concurrents émergents** → WhatsApp API commence à apparaître

### 🎯 Recommandations

1. **Court terme** (1 mois)
   - Analyser les 21,046 clients restants (budget additionnel)
   - Cibler les clients inactifs pour campagnes de réactivation
   - Monitorer WhatsApp API comme concurrent émergent

2. **Moyen terme** (3 mois)
   - Automatiser le scraping incrémental (hebdomadaire)
   - Créer des alertes en temps réel sur nouveaux concurrents
   - Segmenter les clients par volume publicitaire

3. **Long terme** (6 mois)
   - Analyse prédictive : identifier clients à fort potentiel
   - Benchmarking concurrentiel automatisé
   - API publique pour exports automatisés

---

## 🔧 Technologies & Stack

| Catégorie | Technologies |
|-----------|-------------|
| **Backend** | Python 3.11+ |
| **Scraping** | Apify API, Meta Ad Library Actor |
| **Database** | MongoDB (collections: stores, ads_metrics) |
| **Analytics** | pandas, numpy |
| **Visualization** | Streamlit, Plotly |
| **Costs Tracking** | Apify API (monthly_usage) |
| **Logging** | Python logging |

---

## 🚨 Gestion des Coûts

### Budget Tracking en Temps Réel

Le système intègre un **CostTracker** qui :
- ✅ Lit les coûts depuis l'API Apify (`monthly_usage`)
- ✅ Alerte à 60%, 80%, 90%, 100% du budget
- ✅ Arrête automatiquement à 100%
- ✅ Estime les clients restants possibles

**Exemple output :**
```
💰 COÛT SESSION
──────────────────────────────────────────────────────
   Batch actuel : $0.0234
   Session totale : $4.87 / $5.00 🟠
   Restant : $0.13 (2.6%)
   Clients traités : 718
──────────────────────────────────────────────────────
```

### Scripts Disponibles

```bash
# Vérifier les coûts
python scripts/view_costs.py

# Analyse rapide
python scripts/quick_cost_check.py
```

---

## 🛠️ Développement & Maintenance

### Ajouter un nouveau client

```python
from src.discovery.mapper import SiteMapper

mapper = SiteMapper()
result = mapper.process_client("nouveau-client")
```

### Réanalyser un client existant

```bash
python phase2_main.py --client vervane
```

### Nettoyer le cache

```bash
rm -rf data/cache/*
```

---

## Chapter 2
### Conception et Architecture

#### Introduction
Ce chapitre décrit la conception globale et l'architecture technique de la solution. Il précise les exigences fonctionnelles et non fonctionnelles, explique les choix d’architecture, détaille les principaux modules, le modèle de données et les flux de traitement entre la Phase 1 (Discovery & Mapping), la Phase 2 (Classification & Reporting) et le Dashboard. Les schémas proposés visent à clarifier le rôle de chaque composant et leur interaction.

#### 2.1 Exigences Fonctionnelles
| ID | Exigence | Description | Modules associés |
|----|----------|-------------|------------------|
| F1 | Découverte des publicités | Identifier automatiquement les publicités Facebook liées à un domaine client | [src/discovery/ads_collector.py](src/discovery/ads_collector.py), [src/clients/apify_client.py](src/clients/apify_client.py) |
| F2 | Extraction des pages Facebook | Déduire les pages Facebook pertinentes à partir des publicités filtrées | [src/discovery/page_extractor.py](src/discovery/page_extractor.py) |
| F3 | Mapping site ↔ pages | Construire un mapping entre le domaine client et les pages Facebook trouvées | [src/discovery/site_mapper.py](src/discovery/site_mapper.py) |
| F4 | Persistance MongoDB | Sauvegarder mapping et rapports d’analyse | [src/database/mongo_client.py](src/database/mongo_client.py) |
| F5 | Classification des publicités | Déterminer CONVERTY vs CONCURRENT vs UNKNOWN via URLs/DNS | [src/classification/ad_analyzer.py](src/classification/ad_analyzer.py), [src/classification/url_classifier.py](src/classification/url_classifier.py), [src/classification/dns_checker.py](src/classification/dns_checker.py) |
| F6 | Génération de métriques | Calculer ratios et top concurrents | [src/reporting/stats_generator.py](src/reporting/stats_generator.py), [src/analytics/metrics_calculator.py](src/analytics/metrics_calculator.py) |
| F7 | Visualisation | Afficher KPIs, distributions, concurrents | [dashboard.py](dashboard.py), [src/analytics/charts.py](src/analytics/charts.py) |

#### 2.2 Exigences Non Fonctionnelles
| ID | Exigence | Détail | Mise en œuvre |
|----|----------|--------|---------------|
| NF1 | Performance | Limiter appels réseau et I/O | Cache JSON local (ads), TTL DNS, `count` optimisé Apify |
| NF2 | Coût | Maîtrise du budget Apify | Seuils d’alerte, arrêt automatique, budget session (voir Phase 1) |
| NF3 | Fiabilité | Reprise sur erreur | Retries exponentiels Apify, skip clients inactifs, index MongoDB |
| NF4 | Traçabilité | Logs détaillés | [src/utils/logger.py](src/utils/logger.py), traces par batch et par client |
| NF5 | Évolutivité | Modules découplés | Packages `discovery`, `classification`, `analytics`, `database` |

#### 2.3 Architecture Logicielle
L’architecture est organisée en modules spécialisés, orchestrés par des points d’entrée:
- Point d’entrée Phase 1: [phase1_main.py](phase1_main.py) — Discovery & Mapping, coûts réels Apify, persistance mapping.
- Point d’entrée Phase 2: [phase2_main.py](phase2_main.py) — Classification détaillée par pages, agrégation de concurrents, persistance des rapports.
- Dashboard: [dashboard.py](dashboard.py) — Lecture MongoDB, calcul de métriques et visualisations interactives.

Principaux modules:
- Découverte: [src/discovery/site_mapper.py](src/discovery/site_mapper.py), [src/discovery/ads_collector.py](src/discovery/ads_collector.py), [src/discovery/page_extractor.py](src/discovery/page_extractor.py)
- Classification: [src/classification/ad_analyzer.py](src/classification/ad_analyzer.py), [src/classification/url_classifier.py](src/classification/url_classifier.py), [src/classification/dns_checker.py](src/classification/dns_checker.py)
- Données & Persistance: [src/database/mongo_client.py](src/database/mongo_client.py), [config/settings.py](config/settings.py)
- Analytics & UI: [src/analytics/data_loader.py](src/analytics/data_loader.py), [src/analytics/metrics_calculator.py](src/analytics/metrics_calculator.py), [src/analytics/charts.py](src/analytics/charts.py)
- Utilitaires: [src/utils/batch_manager.py](src/utils/batch_manager.py), [src/utils/cost_tracker.py](src/utils/cost_tracker.py), [src/utils/simple_cache.py](src/utils/simple_cache.py)

#### 2.4 Diagramme de Flux (Phase 1 → Phase 2 → Dashboard)
Le pipeline se déroule en trois étapes complémentaires: découverte, classification et visualisation.

```mermaid
flowchart LR
  A[Stores (MongoDB)] -->|Batch load| B[phase1_main.py]
  B --> C[SiteMapper]
  C --> D[AdsCollector]
  D --> E[ApifyFacebookAdsClient]
  D -->|Filtrage domaine| F[Pages Facebook]
  C --> G[Mapping: site ↔ pages]
  G --> H[(MongoDB ads_metrics type=mapping)]
  H --> I[phase2_main.py]
  I --> J[AdAnalyzer]
  J --> K[URLClassifier + DNSChecker]
  J --> L[Rapport (metrics, concurrents)]
  L --> M[(MongoDB ads_metrics type=report)]
  M --> N[Dashboard Streamlit]
  N --> O[MetricsCalculator + ChartGenerator]
```

Explications:
- Filtres stricts en Phase 1 (domaine exact dans les URLs) pour réduire bruit et coûts.
- Persistance en `ads_metrics` avec `type='mapping'` (Phase 1) et `type='report'` (Phase 2).
- Le Dashboard lit les deux types: KPIs (Phase 1) et analyse concurrentielle (Phase 2).

#### 2.5 Modèle de Données
Deux sous-types coexistent dans la collection `ads_metrics`:
- Documents `mapping` (Phase 1): statut d’activité, pages Facebook découvertes, métadonnées de traitement.
- Documents `report` (Phase 2): métriques agrégées, détails par page, concurrents.

Extraits représentatifs: voir [Structure des Données](#-structure-des-données).

Index principaux (voir [src/database/mongo_client.py](src/database/mongo_client.py)):
- `idx_client_type (client_id, type)` pour requêtes ciblées.
- `idx_analyzed_desc (analyzed_at)` pour derniers rapports.
- `idx_type_timestamp (type, timestamp)` pour tri temporel.

#### 2.6 Mécanismes Techniques Clés
- Gestion des coûts: [src/utils/cost_tracker.py](src/utils/cost_tracker.py) suit la session Apify, applique seuils et arrêt.
- Cache des ads: [src/utils/simple_cache.py](src/utils/simple_cache.py) stocke les ads filtrées par domaine (TTL configurable).
- DNS intelligence: [src/classification/dns_checker.py](src/classification/dns_checker.py) combine A record, CNAME, NS avec cache TTL.
- Retries réseau: [src/clients/apify_client.py](src/clients/apify_client.py) intègre des retries exponentiels pour la collecte.

#### 2.7 Graphes et Visualisations (Dashboard)
- Répartition Actifs/Inactifs (pie): illustre la part de clients en activité détectée en Phase 1.
- Distribution du volume d’ads (bar): histogrammes séparés pour actifs et inactifs.
- Séries temporelles (line/area): progression cumulée des clients traités et nouveaux par jour.
- Top concurrents (bar horizontal): nombre d’ads par domaine concurrent; pie plateformes (Shopify/YouCan/etc.).

Chaque graphe est alimenté par `MetricsCalculator` et rendu par `ChartGenerator`. Les filtres (période, seuil d’ads, statut) modulent la vue et les agrégations.

#### 2.8 Justification des Choix d’Architecture
- Découplage fort entre collecte, classification et UI pour faciliter l’évolution.
- MongoDB centralise mappings et rapports, avec indexes adaptés aux requêtes fréquentes.
- Filtrage strict des ads en Phase 1 pour limiter coûts et faux positifs.
- Vérification DNS pour robustesse de la classification au-delà du simple matching d’URL.
- Dashboard Streamlit pour la rapidité d’itération et une visualisation interactive immédiate.

#### Conclusion
La conception proposée garantit une chaîne de traitement fiable, maîtrisée en coûts et extensible. Les modules sont faiblement couplés, les données sont structurées pour l’analyse, et les visuels rendent l’information exploitable pour le pilotage. Cette base solide permet d’aborder le chapitre suivant consacré à la mise en œuvre détaillée et aux expérimentations.
