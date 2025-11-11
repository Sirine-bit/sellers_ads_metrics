import os
import sys
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.mongo_client import MongoDBClient
from bson import ObjectId
from bson import json_util
import json


def detect_type(doc):
    # Heuristiques simples
    if 'mappings' in doc and isinstance(doc.get('mappings'), list):
        return 'mapping'
    if 'metrics' in doc or 'facebook_pages' in doc or 'analyzed_at' in doc:
        return 'report'
    # fallback: unknown
    return 'unknown'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migration: add "type" field to existing docs in converty.ads_metrics')
    parser.add_argument('--apply', action='store_true', help='Apply updates (default: dry-run)')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of documents to process (0 = no limit)')
    args = parser.parse_args()

    client = MongoDBClient()
    coll = client.db['ads_metrics']

    # Query documents missing 'type'
    query = { 'type': { '$exists': False } }
    cursor = coll.find(query)

    total = 0
    to_update = []

    for doc in cursor:
        total += 1
        if args.limit and total > args.limit:
            break
        new_type = detect_type(doc)
        to_update.append((doc['_id'], new_type))

    print(f"Found {len(to_update)} documents without 'type' (total scanned: {total})")
    counts = {}
    for _id, t in to_update:
        counts[t] = counts.get(t, 0) + 1
    print("Counts by assigned type:")
    for k, v in counts.items():
        print(f"  - {k}: {v}")

    if not to_update:
        print('Nothing to do.')
        client.close()
        sys.exit(0)

    if not args.apply:
        print('\nDry run (no changes applied). Use --apply to perform the updates.')
        client.close()
        sys.exit(0)

    # Apply updates
    updated = 0
    for _id, t in to_update:
        res = coll.update_one({'_id': _id}, {'$set': {'type': t}})
        if res.modified_count > 0:
            updated += 1

    print(f'Applied updates: {updated}/{len(to_update)} documents updated.')
    client.close()
