import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.database.mongo_client import MongoDBClient
from datetime import datetime

c = MongoDBClient()
# Insert mapping-like doc
mapping = {
    'client_id': 'test-client',
    'total_sites': 1,
    'mappings': [{'site': 'test-client.converty.shop', 'total_ads': 0, 'fb_pages': [], 'mapped_at': datetime.now().isoformat()}],
    'created_at': datetime.utcnow() if hasattr(datetime, 'utcnow') else datetime.now(),
    'type': 'mapping'
}
res1 = c.db['ads_metrics'].insert_one(mapping)
print('Inserted mapping id:', res1.inserted_id)

# Insert report-like doc
report = {
    'client_slug': 'test-client',
    'domain': 'test-client.converty.shop',
    'analyzed_at': datetime.now().isoformat(),
    'metrics': {'total_ads': 5, 'converty_ads': 2, 'concurrent_ads': 3},
    'facebook_pages': [],
    'competitors': [],
    'created_at': datetime.utcnow() if hasattr(datetime, 'utcnow') else datetime.now(),
    'type': 'report'
}
res2 = c.db['ads_metrics'].insert_one(report)
print('Inserted report id:', res2.inserted_id)
