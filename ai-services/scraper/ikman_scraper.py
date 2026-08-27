"""
SmartRentAI — Ikman.lk Property Scraper
========================================
Scrapes rental listings from ikman.lk and saves them directly into MySQL
so they appear immediately in the frontend dashboard.

Usage:
    python ikman_scraper.py --pages 3 --district Colombo
    python ikman_scraper.py --pages 5           # all districts
    python ikman_scraper.py --pages 3 --no-db   # save CSV/JSON only

Requirements:
    pip install requests beautifulsoup4 mysql-connector-python
"""

import time, json, csv, argparse, re, os
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

try:
    import mysql.connector
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
}

BASE_URL = 'https://ikman.lk'

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'port':     int(os.environ.get('DB_PORT', 3306)),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'smartrentai'),
    'charset':  'utf8mb4',
}

# System user ID to assign scraped listings (admin user id=1)
SYSTEM_USER_ID = 1

DISTRICT_PATHS = {
    'Colombo':      '/en/ads/colombo/houses-for-rent',
    'Kandy':        '/en/ads/kandy/houses-for-rent',
    'Galle':        '/en/ads/galle/houses-for-rent',
    'Negombo':      '/en/ads/negombo/houses-for-rent',
    'Kurunegala':   '/en/ads/kurunegala/houses-for-rent',
    'Gampaha':      '/en/ads/gampaha/houses-for-rent',
    'Ratnapura':    '/en/ads/ratnapura/houses-for-rent',
    'Jaffna':       '/en/ads/jaffna/houses-for-rent',
    'Batticaloa':   '/en/ads/batticaloa/houses-for-rent',
    'Anuradhapura': '/en/ads/anuradhapura/houses-for-rent',
    'Matara':       '/en/ads/matara/houses-for-rent',
    'Kalutara':     '/en/ads/kalutara/houses-for-rent',
    'Badulla':      '/en/ads/badulla/houses-for-rent',
    'Trincomalee':  '/en/ads/trincomalee/houses-for-rent',
}

DISTRICT_COORDS = {
    'Colombo':     (6.9271, 79.8612), 'Gampaha':     (7.0914, 80.0000),
    'Kalutara':    (6.5854, 79.9607), 'Kandy':       (7.2906, 80.6337),
    'Matale':      (7.4675, 80.6234), 'Nuwara_Eliya':(6.9497, 80.7891),
    'Galle':       (6.0535, 80.2210), 'Matara':      (5.9549, 80.5550),
    'Hambantota':  (6.1246, 81.1185), 'Jaffna':      (9.6615, 80.0255),
    'Kurunegala':  (7.4867, 80.3647), 'Ratnapura':   (6.6828, 80.3992),
    'Kegalle':     (7.2513, 80.3464), 'Badulla':     (6.9934, 81.0550),
    'Negombo':     (7.2094, 79.8391), 'Anuradhapura':(8.3114, 80.4037),
    'Batticaloa':  (7.7310, 81.6924), 'Trincomalee': (8.5874, 81.2152),
}

PROVINCE_MAP = {
    'Colombo':'Western','Gampaha':'Western','Kalutara':'Western',
    'Kandy':'Central','Matale':'Central','Nuwara_Eliya':'Central',
    'Galle':'Southern','Matara':'Southern','Hambantota':'Southern',
    'Jaffna':'Northern','Kurunegala':'North Western','Ratnapura':'Sabaragamuwa',
    'Kegalle':'Sabaragamuwa','Badulla':'Uva','Negombo':'Western',
    'Anuradhapura':'North Central','Batticaloa':'Eastern','Trincomalee':'Eastern',
}

# ── HTTP helpers ──────────────────────────────────────────────────────────────
def get_page(url: str, retries: int = 3) -> BeautifulSoup | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, 'html.parser')
            if resp.status_code == 429:
                print(f"  ⏳ Rate limited — waiting 30s …")
                time.sleep(30)
            elif resp.status_code == 403:
                print(f"  🚫 Blocked (403) on {url}")
                return None
        except requests.RequestException as e:
            print(f"  ⚠ Request error (attempt {attempt+1}): {e}")
            time.sleep(5 * (attempt + 1))
    return None


# ── Parsing helpers ───────────────────────────────────────────────────────────
def extract_price(text: str) -> float | None:
    text = re.sub(r'[,\s]', '', text.upper())
    m = re.search(r'(\d+(?:\.\d+)?)', text)
    return float(m.group(1)) if m else None


def infer_type(title: str) -> str:
    t = title.lower()
    if 'apartment' in t or 'flat' in t: return 'apartment'
    if 'room' in t or 'annex' in t:     return 'room'
    if 'villa' in t:                    return 'villa'
    return 'house'


def extract_beds(title: str) -> int:
    m = re.search(r'(\d+)\s*(?:bed|bedroom|br)', title, re.I)
    return int(m.group(1)) if m else 2


def extract_listing(card, district: str) -> dict | None:
    try:
        title_el = (card.select_one('h2.listing-title') or
                    card.select_one('.title') or
                    card.select_one('h2') or
                    card.select_one('h3'))
        title = title_el.get_text(strip=True) if title_el else ''
        if not title:
            return None

        price_el   = card.select_one('.price, .listing-price, [class*="price"]')
        price_text = price_el.get_text(strip=True) if price_el else ''
        price      = extract_price(price_text)

        loc_el   = card.select_one('.location, [class*="location"]')
        location = loc_el.get_text(strip=True) if loc_el else district

        link_el = card.select_one('a[href]')
        url     = (BASE_URL + link_el['href']
                   if link_el and link_el['href'].startswith('/') else '')

        img_el = card.select_one('img[src], img[data-src]')
        image  = ''
        if img_el:
            image = img_el.get('src') or img_el.get('data-src', '')
            if image and image.startswith('//'):
                image = 'https:' + image

        lat, lng = DISTRICT_COORDS.get(district, (7.0, 80.0))

        return {
            'title':         title[:200],
            'price':         price or 0,
            'price_text':    price_text,
            'location':      location[:300],
            'district':      district,
            'province':      PROVINCE_MAP.get(district, 'Unknown'),
            'latitude':      lat,
            'longitude':     lng,
            'source_url':    url,
            'image_url':     image,
            'source':        'ikman.lk',
            'scraped_at':    datetime.now().isoformat(),
            'property_type': infer_type(title),
            'bedrooms':      extract_beds(title),
            'bathrooms':     1,
            'description':   f"Scraped from ikman.lk — {location}",
        }
    except Exception as e:
        print(f"  ⚠ Parse error: {e}")
        return None


# ── Scraping ──────────────────────────────────────────────────────────────────
def scrape_district(district: str, path: str, max_pages: int) -> list[dict]:
    listings = []
    for page_num in range(1, max_pages + 1):
        url  = f"{BASE_URL}{path}?page={page_num}"
        print(f"    Page {page_num}: {url}")
        soup = get_page(url)
        if soup is None:
            break

        # Try multiple card selectors (ikman changes its markup)
        cards = (soup.select('.listing-item') or
                 soup.select('[class*="listing-item"]') or
                 soup.select('li.item') or
                 soup.select('article'))

        if not cards:
            print(f"    No cards on page {page_num} — stopping district.")
            break

        new = 0
        for card in cards:
            item = extract_listing(card, district)
            if item and item['price'] > 0:
                listings.append(item)
                new += 1

        print(f"    +{new} valid listings (total: {len(listings)})")
        time.sleep(2)

    return listings


# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    if not DB_AVAILABLE:
        raise RuntimeError("mysql-connector-python not installed. Run: pip install mysql-connector-python")
    return mysql.connector.connect(**DB_CONFIG)


def ensure_location(cursor, district: str, province: str) -> int:
    cursor.execute(
        'SELECT id FROM locations WHERE district = ? LIMIT 1', (district,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    lat, lng = DISTRICT_COORDS.get(district, (7.0, 80.0))
    cursor.execute(
        'INSERT INTO locations (city, district, province, latitude, longitude) VALUES (%s, %s, %s, %s, %s)',
        (district, district, province, lat, lng)
    )
    return cursor.lastrowid


def save_to_db(listings: list[dict]) -> tuple[int, int]:
    conn   = get_db()
    cursor = conn.cursor()
    inserted = 0
    skipped  = 0

    for item in listings:
        try:
            # Check duplicate by source_url
            cursor.execute(
                'SELECT id FROM properties WHERE address_line = %s LIMIT 1',
                (item['source_url'][:300],)
            )
            if cursor.fetchone():
                skipped += 1
                continue

            location_id = ensure_location(cursor, item['district'], item['province'])

            cursor.execute("""
                INSERT INTO properties
                  (landlord_id, location_id, title, description, property_type,
                   bedrooms, bathrooms, monthly_rent, address_line,
                   latitude, longitude, status, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'available',NOW())
            """, (
                SYSTEM_USER_ID,
                location_id,
                item['title'],
                item['description'],
                item['property_type'],
                item['bedrooms'],
                item['bathrooms'],
                item['price'],
                item['source_url'][:300],
                item['latitude'],
                item['longitude'],
            ))
            prop_id = cursor.lastrowid

            # Store scraped image URL if present
            if item['image_url']:
                cursor.execute("""
                    INSERT INTO property_images (property_id, url, is_primary, sort_order)
                    VALUES (%s, %s, 1, 0)
                """, (prop_id, item['image_url']))

            conn.commit()
            inserted += 1

        except Exception as e:
            conn.rollback()
            print(f"  ⚠ DB error for '{item['title'][:40]}': {e}")
            skipped += 1

    cursor.close()
    conn.close()
    return inserted, skipped


# ── Output helpers ────────────────────────────────────────────────────────────
def save_files(listings: list[dict], out_dir: str = 'output'):
    Path(out_dir).mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    json_path = f"{out_dir}/scraped_{ts}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(listings, f, ensure_ascii=False, indent=2)

    csv_path = f"{out_dir}/scraped_{ts}.csv"
    if listings:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=listings[0].keys())
            w.writeheader()
            w.writerows(listings)

    return json_path, csv_path


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='SmartRentAI — Ikman.lk Scraper')
    parser.add_argument('--pages',    type=int, default=3,    help='Pages per district')
    parser.add_argument('--district', type=str, default=None, help='Single district (e.g. Colombo)')
    parser.add_argument('--out',      type=str, default='output')
    parser.add_argument('--no-db',    action='store_true',    help='Skip DB save, output files only')
    args = parser.parse_args()

    targets = (
        {args.district: DISTRICT_PATHS[args.district]}
        if args.district and args.district in DISTRICT_PATHS
        else DISTRICT_PATHS
    )

    print(f"\n🚀 SmartRentAI Scraper")
    print(f"   Districts : {list(targets.keys())}")
    print(f"   Pages/dist: {args.pages}")
    print(f"   Save to DB: {not args.no_db}\n")

    all_listings = []
    for district, path in targets.items():
        print(f"\n📍 {district}")
        items = scrape_district(district, path, args.pages)

        # Also scrape apartments
        apt_path = path.replace('houses', 'apartments')
        if apt_path != path:
            items += scrape_district(district, apt_path, max(1, args.pages // 2))

        print(f"  ✅ {district}: {len(items)} listings")
        all_listings.extend(items)

    print(f"\n📦 Total scraped: {len(all_listings)}")

    # Save files always
    json_path, csv_path = save_files(all_listings, args.out)
    print(f"  💾 JSON: {json_path}")
    print(f"  💾 CSV:  {csv_path}")

    # Save to DB
    if not args.no_db and all_listings:
        print(f"\n🗄️  Saving to MySQL …")
        try:
            inserted, skipped = save_to_db(all_listings)
            print(f"  ✅ Inserted: {inserted}  |  Skipped (duplicate): {skipped}")
            print(f"  🌐 View at http://localhost:3000/search")
        except Exception as e:
            print(f"  ❌ DB error: {e}")
            print(f"     Use --no-db flag to skip database and save files only.")

    print(f"\n🎉 Done!")


if __name__ == '__main__':
    main()
