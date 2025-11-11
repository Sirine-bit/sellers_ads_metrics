import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.mongo_client import MongoDBClient
import json
from bson import json_util

if __name__ == '__main__':
    try:
        c = MongoDBClient()
        docs = list(c.db['ads_metrics'].find().sort('created_at', -1).limit(10))
        if not docs:
            print('No documents found in converty.ads_metrics')
        for d in docs:
            print(json.dumps(d, default=json_util.default, indent=2))
    except Exception as e:
        print('ERROR:', e)
        import traceback
        traceback.print_exc()
