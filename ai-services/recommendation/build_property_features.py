"""
build_property_features.py — Phase 3
====================================
Enrich the recommender with REAL property data from our own system:

  1. GET http://localhost:5000/api/properties (paginated) -> all live properties
  2. GET http://localhost:5000/api/location/all (proxies :8004) -> SafeRent scores
     + breakdown (hospital / transport / flood / disaster) for all 25 districts
  3. Join into a property feature matrix
  4. Save -> data/property_features.csv

Run:  python build_property_features.py
(Backend :5000 and location-intelligence :8004 must be running.)
"""

import os
import re
import sys
import requests
import pandas as pd

API   = os.environ.get('API_URL', 'http://localhost:5000/api')
OUT_DIR  = os.path.join(os.path.dirname(__file__), 'data')
OUT_PATH = os.path.join(OUT_DIR, 'property_features.csv')


def _norm(d: str) -> str:
    """Normalise a district name for matching ('Nuwara Eliya' == 'Nuwara_Eliya')."""
    return re.sub(r'[ _]', '', str(d)).lower()


def fetch_all_properties():
    """Page through /api/properties until everything is collected."""
    props, page, limit = [], 1, 100
    while True:
        r = requests.get(f'{API}/properties', params={'page': page, 'limit': limit}, timeout=20)
        r.raise_for_status()
        payload = r.json()
        batch = payload.get('data', [])
        props.extend(batch)
        total = payload.get('total', len(props))
        if len(props) >= total or not batch:
            break
        page += 1
    return props


def fetch_saferent():
    """Return { normalized_district: {saferent, hospital, transport, flood, disaster} }."""
    r = requests.get(f'{API}/location/all', timeout=20)
    r.raise_for_status()
    out = {}
    for d in r.json():
        b = d.get('breakdown', {})
        out[_norm(d['district'])] = {
            'saferent_score':  d.get('safe_score'),
            'hospital_score':  b.get('hospital_access'),
            'transport_score': b.get('transport_access'),
            'flood_safety':    b.get('flood_safety'),
            'disaster_safety': b.get('disaster_safety'),
        }
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    try:
        properties = fetch_all_properties()
        saferent   = fetch_saferent()
    except requests.exceptions.RequestException as e:
        print('ERROR: could not reach the API. Make sure backend :5000 and '
              'location-intelligence :8004 are running.')
        print(f'Detail: {e}')
        sys.exit(1)

    print(f'Fetched {len(properties)} properties and {len(saferent)} district SafeRent scores.')

    rows = []
    unmatched = set()
    for p in properties:
        key = _norm(p.get('district'))
        sr  = saferent.get(key)
        if sr is None:
            unmatched.add(p.get('district'))
            sr = {'saferent_score': None, 'hospital_score': None, 'transport_score': None,
                  'flood_safety': None, 'disaster_safety': None}
        rows.append({
            'property_id':    p['id'],
            'title':          p.get('title'),
            'district':       p.get('district'),
            'city':           p.get('city'),
            'price':          p.get('monthly_rent'),
            'bedrooms':       p.get('bedrooms'),
            'bathrooms':      p.get('bathrooms'),
            'property_type':  p.get('property_type'),
            'furnished':      p.get('furnished'),
            **sr,
        })

    df = pd.DataFrame(rows)
    df['price']    = pd.to_numeric(df['price'], errors='coerce')
    df['bedrooms'] = pd.to_numeric(df['bedrooms'], errors='coerce')

    # Fill any missing SafeRent (unmatched districts) with column means so the
    # property still participates in similarity matching.
    for col in ['saferent_score', 'hospital_score', 'transport_score', 'flood_safety', 'disaster_safety']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if df[col].isna().any():
            df[col] = df[col].fillna(round(df[col].mean(), 1))

    df.to_csv(OUT_PATH, index=False)

    # ── Report ──────────────────────────────────────────────────────────────
    print(f'\nSaved {len(df):,} rows -> {OUT_PATH}')
    print(f'Columns: {list(df.columns)}')
    if unmatched:
        print(f'WARNING: districts with no SafeRent match (filled with mean): {sorted(unmatched)}')

    print('\n' + '=' * 90)
    print('FIRST 15 PROPERTY FEATURES')
    print('=' * 90)
    with pd.option_context('display.max_columns', None, 'display.width', 220):
        print(df.head(15).to_string(index=False))

    print('\n' + '=' * 90)
    print('SUMMARY')
    print('=' * 90)
    print('\n[properties per district]')
    print(df['district'].value_counts().to_string())
    print('\n[property_type]')
    print(df['property_type'].value_counts().to_string())
    print('\n[price / bedrooms / saferent]')
    print(df[['price', 'bedrooms', 'saferent_score', 'hospital_score', 'transport_score']]
          .describe().round(1).to_string())


if __name__ == '__main__':
    main()
