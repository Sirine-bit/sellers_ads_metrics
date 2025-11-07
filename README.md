📚 README - PHASE 1: DISCOVERY & MAPPING
📋 Vue d'ensemble du projet
Contexte
Converty est une startup tunisienne qui crée des sites e-commerce pour ses clients. Le profit de Converty dépend directement des ventes de ses clients. Il est donc crucial de monitorer leur activité publicitaire sur Facebook pour :

Détecter les clients inactifs
Identifier ceux qui utilisent d'autres plateformes
Intervenir proactivement pour maintenir l'engagement

Objectif de la Phase 1
Créer un système automatisé qui, pour chaque client, identifie :

Quels sites possède le client (ex: ravino.converty.shop, ravino-shop.tn)
Quelles pages Facebook sont utilisées pour chaque site
Combien de publicités sont actives pour chaque site


🎯 Problématique métier
Input (Données connues)
Pour chaque client, nous avons :

Slug : Identifiant unique du client (ex: ravino)
Domaine(s) : Liste des sites web du client

Challenge
Un client peut avoir :

Plusieurs sites (site Converty + site personnel)
Plusieurs pages Facebook
Des publicités qui pointent vers différents domaines

Output attendu
Un mapping structuré qui montre :
Client "ravino"
  ├── Site: ravino.converty.shop
  │   └── Page FB: "Ravino Shop" (ID: 123456)
  │       └── 15 publicités actives
  │
  └── Site: ravino-shop.tn
      └── Page FB: "Ravino Boutique" (ID: 789012)
          └── 8 publicités actives

🏗️ Architecture du système - Phase 1
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1 WORKFLOW                          │
└─────────────────────────────────────────────────────────────┘

1. CHARGEMENT DES DONNÉES
   ↓
   data/input/clients.json
   [Liste des clients avec leurs domaines]
   ↓

2. COLLECTE DES PUBLICITÉS (par domaine)
   ↓
   Apify → Facebook Ad Library
   "Récupère toutes les ads contenant le domaine"
   ↓

3. EXTRACTION DES PAGES FACEBOOK
   ↓
   Analyse des publicités collectées
   "Identifie les pages FB qui ont publié ces ads"
   ↓

4. CRÉATION DU MAPPING
   ↓
   Association Site ↔ Pages Facebook
   "Calcul du niveau de confiance"
   ↓

5. SAUVEGARDE
   ↓
   data/output/mappings/[client]_mapping_[timestamp].json
   "Résultat final structuré"

📁 Structure complète du projet
sellers-ads-metrics/
│
├── .env                          # Configuration secrète (TOKEN, etc.)
├── .env.example                  # Exemple de configuration
├── .gitignore                    # Fichiers à ignorer par Git
├── requirements.txt              # Dépendances Python
├── README.md                     # Ce fichier
├── main.py                       # 🚀 Point d'entrée principal
├── test_apify.py                 # Script de test de connexion Apify
│
├── config/
│   └── settings.py               # Configuration centralisée
│
├── src/
│   ├── __init__.py
│   │
│   ├── clients/                  # Clients externes (APIs)
│   │   ├── __init__.py
│   │   └── apify_client.py       # Interface avec Apify
│   │
│   ├── discovery/                # Logique métier principale
│   │   ├── __init__.py
│   │   ├── ads_collector.py      # Collecte des publicités
│   │   ├── page_extractor.py     # Extraction des pages FB
│   │   └── site_mapper.py        # Création du mapping
│   │
│   └── utils/                    # Utilitaires
│       ├── __init__.py
│       └── logger.py             # Configuration des logs
│
└── data/
    ├── input/
    │   └── clients.json          # 📥 FICHIER À CONFIGURER
    │
    └── output/
        └── mappings/             # 📤 Résultats générés
            └── [client]_mapping_[date].json

📂 Description détaillée des fichiers
🔧 Fichiers de configuration
.env
Rôle : Contient les credentials secrets (ne jamais commit sur Git)
envAPIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxx
APIFY_ACTOR_NAME=apify/meta-ad-library-scraper
DEFAULT_COUNTRY=TN
requirements.txt
Rôle : Liste toutes les bibliothèques Python nécessaires
apify-client==1.7.1      # Pour communiquer avec Apify
python-dotenv==1.0.0     # Pour charger les variables .env
pydantic==2.5.0          # Validation de données
colorlog==6.8.0          # Logs colorés
config/settings.py
Rôle : Centralise toute la configuration de l'application

Charge les variables d'environnement depuis .env
Définit les chemins des dossiers
Valide que les configurations obligatoires sont présentes

Fonctions principales :

Settings.validate() : Vérifie que APIFY_API_TOKEN existe
settings.APIFY_API_TOKEN : Accès au token
settings.MAPPINGS_DIR : Chemin du dossier de sortie


🔌 Clients externes
src/clients/apify_client.py
Rôle : Interface avec l'API Apify pour récupérer les publicités Facebook
Classe principale : ApifyFacebookAdsClient
Méthodes importantes :
python# 1. Initialisation
client = ApifyFacebookAdsClient()

# 2. Récupérer TOUTES les ads pour un domaine
ads = client.search_ads_by_domain("ravino.converty.shop")
# Retourne: Liste de publicités (dictionnaires JSON)

# 3. Récupérer UNIQUEMENT les ads actives
active_ads = client.get_all_active_ads_by_domain("ravino.converty.shop")

# 4. Tester la connexion
is_connected = client.test_connection()
Comment ça fonctionne :

Se connecte à Apify avec le token
Lance un Actor Apify (scraper de Meta Ad Library)
Attend que l'Actor finisse sa collecte
Récupère tous les résultats depuis le dataset Apify
Retourne les données structurées

Données retournées (exemple) :
json{
  "id": "12345",
  "page_id": "789",
  "page_name": "Ravino Shop",
  "adCreativeLinkCaption": "ravino.converty.shop",
  "adCreativeBody": "Découvrez nos nouveaux produits",
  "adDeliveryStartTime": "2025-01-15",
  ...
}

🔍 Logique métier (Discovery)
src/discovery/ads_collector.py
Rôle : Collecte et filtre les publicités pour un domaine spécifique
Classe principale : AdsCollector
Workflow :
pythoncollector = AdsCollector()

# 1. Collecter les ads pour un domaine
ads = collector.collect_ads_for_domain("ravino.converty.shop")

# 2. Collecter pour plusieurs domaines
results = collector.collect_all_ads_for_domains([
    "ravino.converty.shop",
    "ravino-shop.tn"
])
# Retourne: {"ravino.converty.shop": [ads1], "ravino-shop.tn": [ads2]}
Filtrage :

Récupère toutes les ads via Apify
Vérifie que l'URL de destination contient le domaine cible
Ne garde que les ads pertinentes

Pourquoi filtrer ?
L'Actor Apify peut retourner des publicités de plusieurs domaines similaires. On ne veut que celles qui pointent EXACTEMENT vers notre domaine.

src/discovery/page_extractor.py
Rôle : Extrait les pages Facebook uniques depuis une liste de publicités
Classe principale : PageExtractor
Méthode principale :
pythonextractor = PageExtractor()

# Extraire les pages depuis des ads
pages = extractor.extract_pages_from_ads(ads)
Ce qu'elle fait :

Parcourt toutes les publicités
Récupère page_id et page_name de chaque ad
Élimine les doublons (une page peut avoir plusieurs ads)
Compte combien d'ads chaque page a publié
Retourne une liste de pages uniques avec statistiques

Résultat :
python[
  {
    "page_id": "123456",
    "page_name": "Ravino Shop",
    "page_url": "facebook.com/ravino.shop",
    "ads_count": 15,
    "sample_ad_ids": ["ad1", "ad2", "ad3", ...]
  }
]

src/discovery/site_mapper.py
Rôle : Crée le mapping complet Site → Pages Facebook pour un client
Classe principale : SiteMapper
Workflow complet :
pythonmapper = SiteMapper()

# 1. Créer le mapping pour un client
client_data = {
    "client_id": "ravino",
    "sites": ["ravino.converty.shop", "ravino-shop.tn"]
}

mapping = mapper.map_client_sites(client_data)

# 2. Sauvegarder le résultat
filepath = mapper.save_mapping(mapping)
Processus pour chaque site :
Site: ravino.converty.shop
  ↓
1. Collecter les ads (AdsCollector)
  ↓
2. Extraire les pages (PageExtractor)
  ↓
3. Calculer la confiance (confidence level)
  ↓
4. Créer le mapping
Calcul de la confiance :
pythonConfiance = (Nombre d'ads de cette page) / (Total d'ads pour ce site)

- HIGH   : >= 70% des ads viennent de cette page
- MEDIUM : >= 30% et < 70%
- LOW    : < 30%
Exemple :
Site "ravino.converty.shop" a 20 ads au total
Page "Ravino Shop" a publié 18 ads
→ Confiance: 18/20 = 90% → HIGH
Résultat final :
json{
  "client_id": "ravino",
  "total_sites": 2,
  "created_at": "2025-10-08T14:30:00",
  "mappings": [
    {
      "site": "ravino.converty.shop",
      "total_ads": 20,
      "mapped_at": "2025-10-08T14:30:00",
      "fb_pages": [
        {
          "page_id": "123456",
          "page_name": "Ravino Shop",
          "page_url": "...",
          "ads_count": 18,
          "confidence": "high",
          "sample_ad_ids": [...]
        }
      ]
    },
    {
      "site": "ravino-shop.tn",
      "total_ads": 5,
      "fb_pages": [...]
    }
  ]
}

🛠️ Utilitaires
src/utils/logger.py
Rôle : Configure un système de logs colorés pour faciliter le debugging
Utilisation :
pythonfrom src.utils.logger import setup_logger

logger = setup_logger(__name__)

logger.debug("Message de debug (cyan)")
logger.info("Message d'info (vert)")
logger.warning("Attention ! (jaune)")
logger.error("Erreur ! (rouge)")
Avantages :

Logs colorés selon le niveau
Affiche le nom du module qui log
Facilite la lecture dans la console


🚀 Points d'entrée
main.py
Rôle : Script principal qui orchestre toute la Phase 1
Workflow :
1. Valider la configuration (.env)
2. Charger les clients depuis clients.json
3. Pour chaque client:
   a. Créer le mapping (SiteMapper)
   b. Sauvegarder le résultat
   c. Afficher un résumé
4. Logs de succès ou d'erreur
Exécution :
bashpython main.py
Logs attendus :
============================================================
🚀 DÉMARRAGE - PHASE 1: DISCOVERY & MAPPING
============================================================

✓ Configuration validée
✓ 1 client(s) chargé(s)
  • ravino: 2 site(s)
    - ravino.converty.shop
    - ravino-shop.tn

############################################################
# CLIENT: ravino
############################################################

--- Traitement du site: ravino.converty.shop ---
🔍 Recherche de TOUTES les ads pour le domaine: ravino.converty.shop
  📊 50 publicités récupérées...
  📊 100 publicités récupérées...
✓ TOTAL: 150 publicités récupérées pour ravino.converty.shop
✓ 20 ads filtrées pour ravino.converty.shop

🔍 Extraction des pages depuis 20 publicités
✓ 1 pages uniques extraites
  • Ravino Shop (ID: 123456) - 20 ads

✓ Mapping créé pour ravino.converty.shop: 1 page(s)

[... même processus pour ravino-shop.tn ...]

💾 Mapping sauvegardé: data/output/mappings/ravino_mapping_20251008_143000.json

============================================================
✅ PHASE 1 TERMINÉE AVEC SUCCÈS
============================================================

test_apify.py
Rôle : Script de test pour vérifier la connexion Apify AVANT de lancer le vrai projet
Utilisation :
bashpython test_apify.py
Ce qu'il fait :

Test de connexion : Vérifie que le token Apify fonctionne
Test de recherche limité : Récupère 10 ads pour tester
Affichage de la structure : Montre les champs disponibles dans les ads
Test complet (optionnel) : Récupère toutes les ads pour un domaine

Quand l'utiliser :

Avant de configurer le projet (vérifier les credentials)
Pour comprendre la structure des données retournées par Apify
Pour debugger des problèmes de collecte


📥 Données d'entrée
data/input/clients.json
Rôle : Fichier de configuration contenant la liste des clients à analyser
Format :
json[
  {
    "Slug": "ravino",
    "Domaine": [
      "ravino.converty.shop",
      "ravino-shop.tn"
    ]
  },
  {
    "Slug": "another-client",
    "Domaine": [
      "client.converty.shop"
    ]
  }
]
Structure :

Slug : Identifiant unique du client (utilisé pour nommer les fichiers de sortie)
Domaine : Liste des sites web du client (SANS http:// ou https://)

⚠️ IMPORTANT :

Les domaines doivent être SANS protocole
✅ Correct : "ravino.converty.shop"
❌ Incorrect : "https://ravino.converty.shop"


📤 Données de sortie
data/output/mappings/[client]_mapping_[timestamp].json
Rôle : Résultat final du mapping pour un client
Nom du fichier :
ravino_mapping_20251008_143000.json
│      │        │        │
│      │        │        └─ Heure (14h30m00s)
│      │        └────────── Date (8 Oct 2025)
│      └─────────────────── Slug du client
└────────────────────────── Préfixe
Contenu complet :
json{
  "client_id": "ravino",
  "total_sites": 2,
  "created_at": "2025-10-08T14:30:00.123456",
  "mappings": [
    {
      "site": "ravino.converty.shop",
      "total_ads": 20,
      "mapped_at": "2025-10-08T14:30:15",
      "fb_pages": [
        {
          "page_id": "123456789",
          "page_name": "Ravino Shop Tunisia",
          "page_url": "https://facebook.com/ravino.shop",
          "ads_count": 18,
          "confidence": "high",
          "sample_ad_ids": [
            "ad_001",
            "ad_002",
            "ad_003",
            "ad_004",
            "ad_005"
          ]
        },
        {
          "page_id": "987654321",
          "page_name": "Ravino Boutique",
          "ads_count": 2,
          "confidence": "low",
          "sample_ad_ids": ["ad_006", "ad_007"]
        }
      ]
    },
    {
      "site": "ravino-shop.tn",
      "total_ads": 5,
      "mapped_at": "2025-10-08T14:30:45",
      "fb_pages": [
        {
          "page_id": "555555555",
          "page_name": "Ravino Personal Shop",
          "ads_count": 5,
          "confidence": "high",
          "sample_ad_ids": [...]
        }
      ]
    }
  ]
}
Interprétation :

total_sites : Nombre de sites du client
mappings : Liste des mappings (un par site)
total_ads : Nombre total d'ads trouvées pour ce site
fb_pages : Liste des pages Facebook qui publient pour ce site
confidence : Niveau de certitude que cette page appartient au client

high : >= 70% des ads viennent de cette page
medium : 30-70%
low : < 30%




⚙️ Installation et Configuration
Prérequis

Python 3.8 ou supérieur
Un compte Apify (gratuit)
Git (optionnel)

Étape 1 : Installation
bash# 1. Cloner ou télécharger le projet
cd sellers-ads-metrics

# 2. Créer un environnement virtuel
python -m venv venv

# 3. Activer l'environnement virtuel
# Sur Windows :
venv\Scripts\activate
# Sur Mac/Linux :
source venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt
Étape 2 : Configuration Apify

Créer un compte Apify

Aller sur https://console.apify.com/
S'inscrire (plan gratuit : $5 de crédit/mois)


Obtenir le token API

Aller dans Settings → Integrations
Copier votre API Token


Configurer le fichier .env

bash   # Copier le fichier exemple
   cp .env.example .env
   
   # Éditer .env avec votre éditeur
   nano .env  # ou notepad .env sur Windows

Remplir les credentials

env   APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxxxxx
   APIFY_ACTOR_NAME=apify/meta-ad-library-scraper
   DEFAULT_COUNTRY=TN
Étape 3 : Configurer les clients
Éditer data/input/clients.json :
json[
  {
    "Slug": "ravino",
    "Domaine": [
      "ravino.converty.shop"
    ]
  }
]
⚠️ Règles importantes :

Le slug doit être unique
Les domaines SANS http:// ou https://
Vérifier l'orthographe des domaines


🚀 Utilisation
Test de connexion (recommandé en premier)
bashpython test_apify.py
Résultat attendu :
✓ Connecté en tant que: votre_username
✅ Connexion réussie !
✓ 10 publicités trouvées (test limité)
Si ça fonctionne, passer à l'étape suivante.
Lancement du projet complet
bashpython main.py
Durée estimée :

1 site avec ~20 ads : 1-2 minutes
1 site avec ~200 ads : 5-10 minutes
Plusieurs sites : additionner les temps

Progression affichée :
📊 50 publicités récupérées...
📊 100 publicités récupérées...
📊 150 publicités récupérées...
✓ TOTAL: 150 publicités récupérées
Résultats
Les fichiers JSON sont générés dans :
data/output/mappings/
├── ravino_mapping_20251008_143000.json
└── another-client_mapping_20251008_150000.json

📊 Interpréter les résultats
Cas 1 : Mapping clair (idéal)
json{
  "site": "ravino.converty.shop",
  "total_ads": 50,
  "fb_pages": [
    {
      "page_name": "Ravino Shop",
      "ads_count": 48,
      "confidence": "high"
    }
  ]
}
Interprétation :
✅ Une seule page Facebook
✅ Confiance élevée (96%)
✅ Le client est bien actif sur Converty

Cas 2 : Plusieurs pages (à vérifier)
json{
  "site": "ravino.converty.shop",
  "total_ads": 50,
  "fb_pages": [
    {
      "page_name": "Ravino Shop",
      "ads_count": 30,
      "confidence": "medium"
    },
    {
      "page_name": "Ravino Boutique",
      "ads_count": 20,
      "confidence": "medium"
    }
  ]
}
Interprétation :
⚠️ Le client utilise 2 pages différentes
⚠️ Peut indiquer un problème ou juste une stratégie marketing
→ Action : Contacter le client pour clarifier

Cas 3 : Aucune publicité
json{
  "site": "ravino.converty.shop",
  "total_ads": 0,
  "fb_pages": []
}
Interprétation :
🚨 Client inactif sur Facebook
🚨 Aucune publicité en cours
→ Action urgente : Contacter le client immédiatement

Cas 4 : Confiance basse
json{
  "fb_pages": [
    {
      "page_name": "Page Random",
      "ads_count": 2,
      "confidence": "low"
    },
    {
      "page_name": "Another Page",
      "ads_count": 3,
      "confidence": "low"
    }
  ]
}
Interprétation :
⚠️ Beaucoup de pages avec peu d'ads chacune
⚠️ Peut indiquer des tests ou des erreurs
→ Action : Vérification manuelle nécessaire

🐛 Résolution des problèmes courants
Erreur : "APIFY_API_TOKEN manquant dans .env"
Cause : Le fichier .env n'existe pas ou est mal configuré
Solution :
bash# 1. Vérifier que .env existe
ls -la .env  # Mac/Linux
dir .env     # Windows

# 2. Si absent, créer depuis l'exemple
cp .env.example .env

# 3. Éditer et ajouter ton token
nano .env

Erreur : "Aucun dataset retourné"
Cause : L'Actor Apify n'a trouvé aucune publicité
Solutions possibles :

Vérifier le domaine : Est-il correct ? Y a-t-il des fautes de frappe ?
Vérifier que le client a des ads actives sur Facebook
Tester manuellement sur Meta Ad Library : https://www.facebook.com/ads/library/


Erreur : "Rate limit exceeded"
Cause : Trop de requêtes Apify en peu de temps
Solutions :

Attendre 1 heure (les limites se réinitialisent)
Réduire le nombre de clients à traiter d'un coup
Upgrader le plan Apify si besoin permanent


Erreur : "Module 'apify_client' not found"
Cause : Les dépendances ne sont pas installées
Solution :
bash# S'assurer que l'environnement virtuel est activé
# Puis réinstaller
pip install -r requirements.txt

Les résultats semblent incorrects
Debug checklist :
bash# 1. Tester la connexion
python test_apify.py

# 2. Vérifier la structure des données retournées
# Dans test_apify.py, regarder les champs disponibles

# 3. Vérifier les logs
# Le programme affiche beaucoup d'infos pendant l'exécution

# 4. Vérifier manuellement sur Facebook
# Aller sur Meta Ad Library et chercher le domaine

🔄 Workflow complet en production
1. Collecte quotidienne (à automatiser plus tard)
bash# Chaque jour à 9h du matin
python main.py
2. Analyse des résultats
python# Script d'analyse (Phase 2)
import json

with open('data/output/mappings/ravino_mapping_latest.json') as f:
    data = json.load(f)

# Vérifier l'activité
for mapping in data['mappings']:
    if mapping['total_ads'] == 0:
        print(f"⚠️ ALERTE: {mapping['site']} - Aucune publicité !")
    elif mapping['total_ads'] < 5:
        print(f"⚠️ ATTENTION: {mapping['site']} - Peu de publicités ({mapping['total_ads']})")
3. Alertes et interventions
Basé sur les résultats :

0 ads → Email + appel urgent au client
< 5 ads → Email de suivi
Confiance low → Vérification manuelle
Plusieurs pages → Clarification avec le client