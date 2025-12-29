"""
Configuration centralisée du projet
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger le fichier .env depuis le répertoire racine du projet
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    """Configuration de l'application"""
    
    # Apify
    APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
    APIFY_ACTOR_NAME = os.getenv('APIFY_ACTOR_NAME', 'apify/meta-ad-library-scraper')
    APIFY_ACTOR_ID = os.getenv('APIFY_ACTOR_ID')

    # Search
    DEFAULT_COUNTRY = os.getenv('DEFAULT_COUNTRY', 'TN')
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    INPUT_DIR = os.path.join(DATA_DIR, 'input')
    OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
    MAPPINGS_DIR = os.path.join(OUTPUT_DIR, 'mappings')
    CLASSIFICATIONS_DIR = os.path.join(OUTPUT_DIR, 'classifications')
    
    @classmethod
    def validate(cls):
        """Valider que toutes les configurations nécessaires sont présentes"""
        if not cls.APIFY_API_TOKEN:
            raise ValueError("APIFY_API_TOKEN manquant dans .env")
        if not cls.APIFY_ACTOR_NAME:
            raise ValueError("APIFY_ACTOR_NAME manquant dans .env")

settings = Settings()