"""
SmartRentAI — Unified Property Scraper
Sites: Ikman.lk · House.lk
Downloads property images locally and saves to MySQL (XAMPP root / no password)
"""

import re
import os
import time
import json
import uuid
import difflib
import argparse
import logging
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('scraper')

# ── Config ───────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent          # SmartRentAI/
UPLOADS_DIR  = PROJECT_ROOT / 'backend' / 'uploads' / 'properties'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ── Canonical district list ──────────────────────────────────
DISTRICTS = [
    'Colombo', 'Gampaha', 'Kalutara',
    'Kandy', 'Nuwara Eliya', 'Matale',
    'Galle', 'Matara', 'Hambantota',
    'Jaffna', 'Kurunegala', 'Anuradhapura',
    'Ratnapura', 'Badulla', 'Kegalle',
    'Trincomalee', 'Batticaloa',
]

IKMAN_DISTRICT_SLUGS = {
    'Colombo':     'colombo',      'Gampaha':    'gampaha',
    'Kalutara':    'kalutara',     'Kandy':      'kandy',
    'Nuwara Eliya':'nuwara-eliya', 'Matale':     'matale',
    'Galle':       'galle',        'Matara':     'matara',
    'Hambantota':  'hambantota',   'Jaffna':     'jaffna',
    'Kurunegala':  'kurunegala',   'Anuradhapura':'anuradhapura',
    'Ratnapura':   'ratnapura',    'Badulla':    'badulla',
    'Kegalle':     'kegalle',      'Trincomalee':'trincomalee',
    'Batticaloa':  'batticaloa',
}

# ── Comprehensive URL-slug → District map ────────────────────
# Root cause fix: ikman listing URLs always end with -for-rent-{district_slug}
# (or -for-rent-{district_slug}-{number} where number is a sub-area/page hint).
# Example: /en/ad/3br-apartment-for-rent-in-colombo-07-for-rent-colombo
#                                                         ^^^^^^^^^^^ take this
# This map converts every plausible ikman URL district slug to a canonical
# district name matching the `locations` table.
_SLUG_DISTRICT: dict[str, str] = {}

# Base district slugs (reverse of IKMAN_DISTRICT_SLUGS)
for _d, _s in IKMAN_DISTRICT_SLUGS.items():
    _SLUG_DISTRICT[_s] = _d

# Colombo suburbs / city areas
_SLUG_DISTRICT.update({
    'nugegoda': 'Colombo', 'dehiwala': 'Colombo', 'mount-lavinia': 'Colombo',
    'maharagama': 'Colombo', 'kotte': 'Colombo', 'malabe': 'Colombo',
    'boralesgamuwa': 'Colombo', 'wellawatte': 'Colombo', 'bambalapitiya': 'Colombo',
    'narahenpita': 'Colombo', 'rajagiriya': 'Colombo', 'nawala': 'Colombo',
    'kirulapone': 'Colombo', 'havelock-town': 'Colombo', 'cinnamon-gardens': 'Colombo',
    'kolonnawa': 'Colombo', 'kaduwela': 'Colombo', 'biyagama': 'Colombo',
    'angoda': 'Colombo', 'mulleriyawa': 'Colombo', 'athurugiriya': 'Colombo',
    'battaramulla': 'Colombo', 'pelawatte': 'Colombo', 'thalawathugoda': 'Colombo',
    'pannipitiya': 'Colombo', 'mirihana': 'Colombo', 'rajigiriya': 'Colombo',
    'moratuwa': 'Colombo', 'rathmalana': 'Colombo', 'piliyandala': 'Colombo',
    'homagama': 'Colombo', 'hokandara': 'Colombo', 'pita-kotte': 'Colombo',
    'ethul-kotte': 'Colombo', 'kalubowila': 'Colombo', 'pepiliyana': 'Colombo',
    'kotikawatta': 'Colombo', 'malwana': 'Colombo', 'kadawatha': 'Colombo',
    'sri-jayawardenepura': 'Colombo', 'attidiya': 'Colombo',
    # Gampaha cities
    'negombo': 'Gampaha', 'ja-ela': 'Gampaha', 'wattala': 'Gampaha',
    'ragama': 'Gampaha', 'kelaniya': 'Gampaha', 'minuwangoda': 'Gampaha',
    'divulapitiya': 'Gampaha', 'mirigama': 'Gampaha', 'nittambuwa': 'Gampaha',
    'veyangoda': 'Gampaha', 'dompe': 'Gampaha', 'kandana': 'Gampaha',
    'ekala': 'Gampaha', 'katunayake': 'Gampaha', 'seeduwa': 'Gampaha',
    'ganemulla': 'Gampaha', 'gampaha': 'Gampaha',
    # Kalutara cities
    'panadura': 'Kalutara', 'horana': 'Kalutara', 'beruwala': 'Kalutara',
    'aluthgama': 'Kalutara', 'matugama': 'Kalutara', 'bandaragama': 'Kalutara',
    'wadduwa': 'Kalutara', 'ingiriya': 'Kalutara',
    # Kandy cities
    'peradeniya': 'Kandy', 'katugastota': 'Kandy', 'gampola': 'Kandy',
    'nawalapitiya': 'Kandy', 'akurana': 'Kandy', 'kundasale': 'Kandy',
    'digana': 'Kandy',
    # Nuwara Eliya
    'hatton': 'Nuwara Eliya', 'norwood': 'Nuwara Eliya', 'talawakele': 'Nuwara Eliya',
    'dikoya': 'Nuwara Eliya',
    # Matale
    'dambulla': 'Matale', 'sigiriya': 'Matale',
    # Galle cities
    'unawatuna': 'Galle', 'hikkaduwa': 'Galle', 'ambalangoda': 'Galle',
    'bentota': 'Galle', 'balapitiya': 'Galle', 'elpitiya': 'Galle',
    'talpe': 'Galle', 'habaraduwa': 'Galle',
    # Matara cities
    'weligama': 'Matara', 'akuressa': 'Matara', 'deniyaya': 'Matara',
    'hakmana': 'Matara', 'kamburupitiya': 'Matara',
    # Hambantota cities
    'tangalle': 'Hambantota', 'tissamaharama': 'Hambantota', 'ambalantota': 'Hambantota',
    'suriyawewa': 'Hambantota',
    # Jaffna cities
    'chavakachcheri': 'Jaffna', 'nallur': 'Jaffna', 'point-pedro': 'Jaffna',
    # Kurunegala cities
    'kuliyapitiya': 'Kurunegala', 'maho': 'Kurunegala', 'ibbagamuwa': 'Kurunegala',
    'nikaweratiya': 'Kurunegala', 'pannala': 'Kurunegala',
    # Anuradhapura cities
    'kekirawa': 'Anuradhapura', 'medawachchiya': 'Anuradhapura',
    # Ratnapura cities
    'embilipitiya': 'Ratnapura', 'balangoda': 'Ratnapura', 'pelmadulla': 'Ratnapura',
    # Badulla cities
    'bandarawela': 'Badulla', 'ella': 'Badulla', 'haputale': 'Badulla',
    'mahiyangana': 'Badulla', 'welimada': 'Badulla', 'hali-ela': 'Badulla',
    # Kegalle cities
    'mawanella': 'Kegalle', 'rambukkana': 'Kegalle', 'warakapola': 'Kegalle',
})

# Print mapping on first import (useful for debugging)
def print_slug_map():
    print('\n=== _SLUG_DISTRICT map ===')
    for slug, district in sorted(_SLUG_DISTRICT.items()):
        print(f'  {slug!r:35s} → {district!r}')
    print(f'Total: {len(_SLUG_DISTRICT)} entries\n')

# ── Location extraction helpers ──────────────────────────────

def _district_from_url(href: str) -> str:
    """
    PRIORITY 1: extract district from the ikman listing card href.

    ikman URL format (confirmed by live inspection):
      /en/ad/{title-slug}-for-rent-{district-slug}[{-number}]

    The LAST occurrence of 'for-rent-' in the slug is always the listing's
    actual district — even when the page being scraped is a different district
    (ikman shows promoted listings from all over SL on every district page).

    Pattern: take everything after the last 'for-rent-' that is purely
    alpha-hyphen (stops at first digit), then look up in _SLUG_DISTRICT.

    Examples:
      .../for-rent-colombo              → 'colombo'     → 'Colombo'
      .../for-rent-colombo-2            → 'colombo'     → 'Colombo'  (digit stripped)
      .../for-rent-nuwara-eliya         → 'nuwara-eliya'→ 'Nuwara Eliya'
      .../colombo-07-for-rent-colombo   → 'colombo'     → 'Colombo'  (last match wins)
      .../in-kelaniya-for-rent-gampaha  → 'gampaha'     → 'Gampaha'
    """
    slug = href.lower()
    # Split on every 'for-(rent|sale|lease)-' and take the LAST segment.
    # This handles the pattern:  ...-for-rent-in-kelaniya-for-rent-gampaha-25
    # where a naive findall greedily captures across an inner 'for-rent-' token.
    parts = re.split(r'for-(?:rent|sale|lease)-', slug)
    if len(parts) < 2:
        return ''
    last_part = parts[-1]          # e.g. 'gampaha-25' / 'colombo' / 'nuwara-eliya'
    # Extract leading alpha-hyphen segment only (stops at first digit)
    m = re.match(r'([a-z]+(?:-[a-z]+)*)', last_part)
    if not m:
        return ''
    location_slug = m.group(1)     # 'gampaha', 'colombo', 'nuwara-eliya', …
    return _SLUG_DISTRICT.get(location_slug, '')


def _district_from_title(title: str) -> str:
    """
    PRIORITY 2: scan title for known district or city names.

    Handles: 'Colombo 07', 'Colombo 7', 'in Kandy', 'Nuwara Eliya', etc.
    Returns canonical district name or ''.
    """
    t = title.lower()

    # Colombo N variants (Colombo 07, Colombo 7, Colombo district)
    if re.search(r'\bcolombo\b', t):
        return 'Colombo'

    # Other canonical districts (longest first to avoid partial matches)
    for d in sorted(DISTRICTS, key=len, reverse=True):
        if d.lower() in t:
            return d

    # City → district fallback (longest slug first)
    for slug, district in sorted(_SLUG_DISTRICT.items(), key=lambda x: len(x[0]), reverse=True):
        city_name = slug.replace('-', ' ')
        if len(city_name) > 4 and city_name in t:
            return district

    return ''


def _fuzzy_district(raw: str) -> str:
    """
    PRIORITY 3 fallback: difflib closest match against canonical district names.
    Only fires when URL + title both fail (e.g. unseen suburb names).
    cutoff=0.75 prevents wild mismatches.
    """
    candidates = [d.lower() for d in DISTRICTS]
    matches = difflib.get_close_matches(raw.lower(), candidates, n=1, cutoff=0.75)
    if matches:
        idx = candidates.index(matches[0])
        return DISTRICTS[idx]
    return ''


def _resolve_district(href: str, title: str, page_slug: str) -> str:
    """
    Full priority chain:
      1. URL path  (most reliable — ikman embeds district at end of every listing href)
      2. Title     (catches 'Colombo 07' in listing name)
      3. Page slug (what we're currently browsing — used only as last resort because
                    ikman shows promoted listings from ALL districts on every page)
    Never returns empty: falls back to page_slug.
    """
    d = _district_from_url(href)
    if d:
        return d
    d = _district_from_title(title)
    if d:
        return d
    # Last resort: page-level slug (may be wrong for promoted cross-district cards)
    page_district = page_slug.replace('-', ' ').title()
    if 'Nuwara' in page_district:
        page_district = 'Nuwara Eliya'
    return page_district or 'Colombo'


# ── Image downloader ─────────────────────────────────────────
BASE_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36'),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def download_image(url: str, referer: str = '') -> str:
    """Download image to local uploads folder. Returns /uploads/properties/filename or ''."""
    if not url or not url.startswith('http'):
        return ''
    try:
        ext = re.search(r'\.(jpe?g|png|webp|gif)', url, re.I)
        ext = ext.group(0).lower() if ext else '.jpg'
        filename = uuid.uuid4().hex + ext
        filepath = UPLOADS_DIR / filename

        img_headers = {**BASE_HEADERS, 'Referer': referer}
        r = requests.get(url, headers=img_headers, timeout=15, stream=True)
        if r.status_code != 200 or 'image' not in r.headers.get('content-type', ''):
            return ''

        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        return f'/uploads/properties/{filename}'
    except Exception as e:
        log.debug(f'Image download failed ({url[:60]}): {e}')
        return ''

# ── DB helpers ───────────────────────────────────────────────
def get_connection():
    import mysql.connector
    return mysql.connector.connect(
        host='localhost', port=3306, user='root', password='',
        database='smartrentai', charset='utf8mb4',
    )

def get_admin_user_id(cur) -> int:
    cur.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1")
    row = cur.fetchone()
    if not row:
        raise RuntimeError('No admin user found. Please register an admin first.')
    return row[0]

def upsert_location(cur, district: str, city: str) -> int:
    cur.execute(
        'SELECT id FROM locations WHERE district=%s AND city=%s LIMIT 1',
        (district, city)
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        'INSERT INTO locations (district, city, province) VALUES (%s, %s, %s)',
        (district, city, '')
    )
    return cur.lastrowid

def get_location_id_for_district(cur, district: str) -> int:
    """
    Return the location_id for a district.  Prefers the row where city=district
    (the 'main' city entry) so repairs don't create extra rows.
    Falls back to any row in that district, then creates one.
    """
    cur.execute(
        'SELECT id FROM locations WHERE district=%s AND city=%s LIMIT 1',
        (district, district)
    )
    row = cur.fetchone()
    if row:
        return row[0]
    # Any row for this district
    cur.execute('SELECT id FROM locations WHERE district=%s LIMIT 1', (district,))
    row = cur.fetchone()
    if row:
        return row[0]
    # Create
    return upsert_location(cur, district, district)

def save_property(cur, prop: dict, admin_id: int) -> int | None:
    # 1) Same source URL already scraped → skip.
    if prop.get('source_url'):
        cur.execute(
            'SELECT id FROM properties WHERE address_line=%s LIMIT 1',
            (prop['source_url'],)
        )
        if cur.fetchone():
            return None

    # 2) Re-listing guard: portals re-post the same physical listing under a NEW
    #    listing id / URL, so the URL check above misses it. The agency reference
    #    code in the title (e.g. "HR312") makes title+rent a reliable identity.
    title = prop.get('title', 'Untitled')[:200]
    rent  = prop.get('monthly_rent') or 0
    if title and title != 'Untitled':
        cur.execute(
            'SELECT id FROM properties WHERE title=%s AND monthly_rent=%s LIMIT 1',
            (title, rent)
        )
        if cur.fetchone():
            return None

    location_id = upsert_location(cur, prop['district'], prop.get('city', prop['district']))

    cur.execute('''
        INSERT INTO properties
            (landlord_id, location_id, title, description, property_type,
             monthly_rent, bedrooms, bathrooms, furnished, address_line, status, is_featured)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        admin_id,
        location_id,
        title,
        prop.get('description', prop.get('title', ''))[:2000],
        prop.get('property_type', 'house'),
        rent,
        prop.get('bedrooms') if prop.get('bedrooms') is not None else 0,
        prop.get('bathrooms') if prop.get('bathrooms') is not None else 0,
        prop.get('furnished', 'unfurnished'),
        prop.get('source_url', '')[:300],
        'available',
        0,
    ))
    prop_id = cur.lastrowid

    local_img = prop.get('local_image', '')
    if local_img:
        cur.execute(
            'INSERT INTO property_images (property_id, url, is_primary, sort_order) VALUES (%s,%s,%s,%s)',
            (prop_id, local_img, 1, 0)
        )
    return prop_id

def save_to_db(listings: list) -> tuple[int, int]:
    conn = get_connection()
    cur  = conn.cursor()
    saved = skipped = 0
    try:
        admin_id = get_admin_user_id(cur)
        log.info(f'Using admin user id={admin_id} for scraped listings')
        for p in listings:
            pid = save_property(cur, p, admin_id)
            if pid:
                saved += 1
            else:
                skipped += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return saved, skipped

# ── Price parsing ─────────────────────────────────────────────
def parse_price(text: str) -> int:
    if not text:
        return 0
    nums = re.sub(r'[^\d]', '', text)
    return int(nums) if nums else 0

# ── Ikman.lk scraper ─────────────────────────────────────────
IKMAN_CATEGORIES = ['house-rentals', 'apartment-rentals']

FURNISHED_RE = re.compile(r'\b(unfurnished|semi.?furnished|fully\s+furnished|furnished)\b', re.I)
BEDS_RE      = re.compile(r'Beds?:\s*(\d+)', re.I)
BATHS_RE     = re.compile(r'Baths?:\s*(\d+)', re.I)

def _ikman_full_res(url: str) -> str:
    return re.sub(r'/\d+/\d+/cropped\.jpg$', '/800/600/cropped.jpg', url)

def _parse_furnished(title: str) -> str:
    m = FURNISHED_RE.search(title)
    if not m:
        return 'unfurnished'
    t = m.group(1).lower()
    if 'unfurnished' in t:
        return 'unfurnished'
    if 'semi' in t:
        return 'semi-furnished'
    return 'furnished'


def diagnose_location_fields(district_slug: str, category: str):
    """
    Print all location-related fields for the first 6 cards of a given page.
    Run with:  python scraper.py --diagnose --district Colombo
    """
    url = f'https://ikman.lk/en/ads/{district_slug}/{category}'
    r   = requests.get(url, headers=BASE_HEADERS, timeout=20)
    soup  = BeautifulSoup(r.content, 'html.parser')
    cards = soup.find_all('a', class_=re.compile('gtm-ad-item'))

    print(f'\n{"="*80}')
    print(f'DIAGNOSIS: {url}')
    print(f'Cards found: {len(cards)}')
    print(f'{"="*80}')

    for i, card in enumerate(cards[:8]):
        href      = card.get('href', '')
        title_el  = card.find(class_=re.compile('title--'))
        title     = title_el.get_text(strip=True) if title_el else ''

        # Every span/div that might contain location text
        loc_els = [el for el in card.find_all(True)
                   if any('location' in c.lower() or 'area' in c.lower()
                          or 'address' in c.lower() or 'city' in c.lower()
                          for c in (el.get('class') or []))]
        loc_texts = [el.get_text(strip=True) for el in loc_els] or ['(no location spans)']

        # All three extraction methods
        from_url   = _district_from_url(href)
        from_title = _district_from_title(title)
        from_page  = district_slug.replace('-', ' ').title()
        if 'Nuwara' in from_page:
            from_page = 'Nuwara Eliya'

        # What the OLD scraper would have done (wrong)
        old_scraper = from_page   # always used page slug
        # What the NEW scraper does
        chosen = _resolve_district(href, title, district_slug)
        mismatch = '  *** OLD WAS WRONG ***' if chosen != old_scraper else ''

        # URL analysis
        all_rent_segs = re.findall(r'for-(?:rent|sale|lease)-([a-z]+(?:-[a-z]+)*)', href.lower())

        print(f'\nCard {i+1}: {title[:85]}')
        print(f'  href                : {href[:100]}')
        last_seg = all_rent_segs[-1] if all_rent_segs else 'none'
        print(f'  for-rent segments   : {all_rent_segs}  -> last={last_seg!r}')
        print(f'  location span(s)    : {loc_texts}')
        print(f'  -- extraction --')
        print(f'  [1] from URL        : {from_url!r}')
        print(f'  [2] from title      : {from_title!r}')
        print(f'  [3] from page slug  : {from_page!r}')
        print(f'  OLD scraper used    : {old_scraper!r}{mismatch}')
        print(f'  NEW scraper uses    : {chosen!r}')

    print(f'\n{"="*80}')
    print('Full _SLUG_DISTRICT map:')
    for slug, district in sorted(_SLUG_DISTRICT.items()):
        print(f'  {slug!r:40s} → {district!r}')
    print(f'Total entries: {len(_SLUG_DISTRICT)}')


def scrape_ikman_page(district_slug: str, category: str, page: int, download_imgs: bool) -> list:
    url = f'https://ikman.lk/en/ads/{district_slug}/{category}'
    if page > 1:
        url += f'?page={page}'
    try:
        r = requests.get(url, headers=BASE_HEADERS, timeout=20)
        if r.status_code != 200:
            log.warning(f'Ikman {url} -> {r.status_code}')
            return []
    except Exception as e:
        log.error(f'Ikman fetch error: {e}')
        return []

    soup  = BeautifulSoup(r.content, 'html.parser')
    cards = soup.find_all('a', class_=re.compile('gtm-ad-item'))
    log.info(f'Ikman [{district_slug}/{category}] page {page}: {len(cards)} cards')

    fallback_bed = fallback_bath = cross_district = 0
    results = []
    for card in cards:
        try:
            title_el   = card.find(class_=re.compile('title--'))
            price_el   = card.find(class_=re.compile('price--'))
            details_el = card.find(class_=re.compile('details--'))
            img_el     = card.find('img', src=re.compile(r'^https'))

            title        = title_el.get_text(strip=True) if title_el else card.get('title', '')
            monthly_rent = parse_price(price_el.get_text() if price_el else '')

            details_text = details_el.get_text(strip=True) if details_el else ''
            beds_m  = BEDS_RE.search(details_text)
            baths_m = BATHS_RE.search(details_text)
            bedrooms  = int(beds_m.group(1))  if beds_m  else None
            bathrooms = int(baths_m.group(1)) if baths_m else None
            if bedrooms  is None: fallback_bed  += 1
            if bathrooms is None: fallback_bath += 1

            raw_img_url = img_el['src'] if img_el else ''
            img_url     = _ikman_full_res(raw_img_url) if raw_img_url else ''

            href       = card.get('href', '')
            source_url = ('https://ikman.lk' + href) if href else url
            prop_type  = 'apartment' if category == 'apartment-rentals' else 'house'

            if not title:
                continue

            # ── FIX: resolve district with priority chain ──────────────
            # Priority 1: URL path (most accurate — ikman embeds actual district at end)
            # Priority 2: listing title text
            # Priority 3: page slug (last resort — may be wrong for promoted cards)
            district = _resolve_district(href, title, district_slug)

            # Track cross-district promoted cards for logging
            page_district = district_slug.replace('-', ' ').title()
            if 'Nuwara' in page_district:
                page_district = 'Nuwara Eliya'
            if district != page_district:
                cross_district += 1
                log.debug(f'Cross-district card: {title[:60]!r} → {district} '
                          f'(page was {page_district})')

            furnished   = _parse_furnished(title)
            local_image = ''
            if download_imgs and img_url:
                local_image = download_image(img_url, referer='https://ikman.lk/')

            results.append({
                'title':         title,
                'monthly_rent':  monthly_rent,
                'local_image':   local_image,
                'source_url':    source_url,
                'property_type': prop_type,
                'district':      district,
                'city':          district,     # city defaults to district; fix_locations.py refines
                'bedrooms':      bedrooms,
                'bathrooms':     bathrooms,
                'furnished':     furnished,
                'description':   f'{title} — scraped from Ikman.lk ({district})',
            })
        except Exception as e:
            log.debug(f'Ikman card parse error: {e}')

    if cross_district:
        log.info(f'  ↳ {cross_district}/{len(results)} cards were cross-district promoted listings '
                 f'(fixed by URL extraction)')
    if fallback_bed or fallback_bath:
        log.info(f'  ↳ beds/baths missing from details div: '
                 f'{fallback_bed}/{len(results)} / {fallback_bath}/{len(results)}')
    return results


def scrape_ikman(districts: list, pages: int, download_imgs: bool) -> list:
    all_results = []
    for district in districts:
        slug = IKMAN_DISTRICT_SLUGS.get(district, district.lower())
        for cat in IKMAN_CATEGORIES:
            for page in range(1, pages + 1):
                items = scrape_ikman_page(slug, cat, page, download_imgs)
                all_results.extend(items)
                time.sleep(1.5)
    return all_results

# ── House.lk scraper ─────────────────────────────────────────
HOUSE_LK_CATEGORIES = ['house', 'apartment']

def scrape_houselk_page(category: str, page: int, download_imgs: bool) -> list:
    url = f'https://house.lk/rent/{category}/'
    if page > 1:
        url += f'page/{page}/'
    try:
        r = requests.get(url, headers=BASE_HEADERS, timeout=20)
        if r.status_code != 200:
            log.warning(f'House.lk {url} -> {r.status_code}')
            return []
    except Exception as e:
        log.error(f'House.lk fetch error: {e}')
        return []

    soup  = BeautifulSoup(r.content, 'html.parser')
    cards = soup.find_all('div', class_='property_listing')
    log.info(f'House.lk [{category}] page {page}: {len(cards)} cards')

    results = []
    for card in cards:
        try:
            h4_a = card.find('h4')
            if not h4_a:
                continue
            link_el    = h4_a.find('a', href=True)
            title      = link_el.get_text(strip=True) if link_el else h4_a.get_text(strip=True)
            source_url = 'https://house.lk' + link_el['href'] if link_el else url

            price_el     = card.find(class_='listing_unit_price_wrapper')
            monthly_rent = parse_price(price_el.get_text() if price_el else '')

            img_el  = card.find('img', attrs={'data-src': True})
            img_url = img_el['data-src'] if img_el else ''

            loc_el   = card.find(class_=re.compile('action_tag_location'))
            loc_text = loc_el.get_text(strip=True) if loc_el else ''
            district = _guess_district(loc_text) or 'Colombo'
            city     = loc_text or district

            if not title:
                continue

            local_image = ''
            if download_imgs and img_url:
                local_image = download_image(img_url, referer='https://house.lk/')

            results.append({
                'title':        title,
                'monthly_rent': monthly_rent,
                'local_image':  local_image,
                'source_url':   source_url,
                'property_type': category,
                'district':     district,
                'city':         city,
                'description':  f'{title} — scraped from House.lk ({city})',
            })
        except Exception as e:
            log.debug(f'House.lk card parse error: {e}')
    return results

def _guess_district(location: str) -> str:
    location_lower = location.lower()
    for d in DISTRICTS:
        if d.lower() in location_lower:
            return d
    for slug, district in sorted(_SLUG_DISTRICT.items(), key=lambda x: len(x[0]), reverse=True):
        city_name = slug.replace('-', ' ')
        if len(city_name) > 4 and city_name in location_lower:
            return district
    return ''

def scrape_houselk(pages: int, download_imgs: bool) -> list:
    all_results = []
    for cat in HOUSE_LK_CATEGORIES:
        for page in range(1, pages + 1):
            items = scrape_houselk_page(cat, page, download_imgs)
            all_results.extend(items)
            time.sleep(1.5)
    return all_results

# ── Main ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='SmartRentAI Property Scraper')
    parser.add_argument('--pages',      type=int, default=2)
    parser.add_argument('--district',   default='all')
    parser.add_argument('--site',       default='all',
                        choices=['all', 'ikman', 'houselk'])
    parser.add_argument('--no-db',      action='store_true',
                        help='Skip DB, print JSON only')
    parser.add_argument('--no-images',  action='store_true',
                        help='Skip image downloads (faster)')
    parser.add_argument('--diagnose',   action='store_true',
                        help='Print all location fields for first 8 cards then exit')
    args = parser.parse_args()

    districts     = DISTRICTS if args.district.lower() == 'all' else [args.district]
    download_imgs = not args.no_images

    if args.diagnose:
        d = districts[0]
        slug = IKMAN_DISTRICT_SLUGS.get(d, d.lower())
        diagnose_location_fields(slug, 'apartment-rentals')
        return

    if download_imgs:
        log.info(f'Images will be downloaded to: {UPLOADS_DIR}')
    else:
        log.info('Image download skipped (--no-images)')

    all_listings = []

    if args.site in ('all', 'ikman'):
        log.info(f'=== Scraping Ikman.lk ({args.pages} pages x {len(districts)} districts) ===')
        all_listings += scrape_ikman(districts, args.pages, download_imgs)

    if args.site in ('all', 'houselk'):
        log.info(f'=== Scraping House.lk ({args.pages} pages) ===')
        all_listings += scrape_houselk(args.pages, download_imgs)

    log.info(f'Total collected: {len(all_listings)} listings')

    if args.no_db:
        import sys
        out = [{k: v for k, v in p.items() if k != 'local_image'} for p in all_listings]
        sys.stdout.buffer.write(json.dumps(out, indent=2, ensure_ascii=False).encode('utf-8'))
        sys.stdout.buffer.write(b'\n')
        return

    log.info('Saving to MySQL...')
    saved, skipped = save_to_db(all_listings)
    log.info(f'Done — saved: {saved}, skipped (duplicates): {skipped}')

if __name__ == '__main__':
    main()
