"""
fix_locations.py — One-time correction for properties with wrong location_id.

Root cause: scraper previously assigned the district of the LIST PAGE being scraped
to all cards on that page. ikman shows promoted listings from any district on every
page, so e.g. Colombo listings scraped while browsing Badulla got district='Badulla'.

Fix: re-parse address_line (which stores the source URL) using _district_from_url()
from the updated scraper, then update location_id to the correct district.

Usage:
    python fix_locations.py            # dry run — shows what would change
    python fix_locations.py --commit   # apply changes
    python fix_locations.py --show-map # print the full slug→district map and exit
"""

import sys
import re
import argparse

# Import the updated scraper's extraction functions
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from scraper import _district_from_url, _district_from_title, _SLUG_DISTRICT, DISTRICTS

def get_connection():
    import mysql.connector
    return mysql.connector.connect(
        host='localhost', port=3306, user='root', password='',
        database='smartrentai', charset='utf8mb4',
    )


def get_or_create_location(cur, district: str) -> int:
    """
    Find the best location_id for a district.
    Prefers the row where city = district (the 'main' city row).
    Falls back to any row with that district.
    Creates a new row only if district is completely absent.
    """
    # Prefer main city row (city = district name)
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

    # Create new row
    cur.execute(
        'INSERT INTO locations (district, city, province) VALUES (%s, %s, %s)',
        (district, district, '')
    )
    return cur.lastrowid


def run(commit: bool):
    conn = get_connection()
    cur  = conn.cursor()

    # ── Step 1: fetch all scraped properties with their current district ──
    cur.execute('''
        SELECT p.id, p.address_line, l.district AS current_district, l.id AS current_loc_id
        FROM properties p
        JOIN locations l ON p.location_id = l.id
        WHERE p.address_line LIKE %s
        ORDER BY p.id
    ''', ('%ikman.lk/en/ad/%',))
    rows = cur.fetchall()
    print(f'\nTotal ikman properties in DB: {len(rows)}')

    # ── Step 2: determine correct district for each ───────────────────────
    updates     = []   # (prop_id, url, old_district, new_district, new_loc_id_placeholder)
    already_ok  = []
    no_match    = []

    for prop_id, address_line, current_district, current_loc_id in rows:
        correct_district = _district_from_url(address_line)

        if not correct_district:
            # Try title-based fallback (address_line is the URL, not a title)
            # but extract a rough title from the URL slug
            slug_m = re.search(r'/en/ad/([^/?#]+)', address_line or '')
            if slug_m:
                pseudo_title = slug_m.group(1).replace('-', ' ')
                correct_district = _district_from_title(pseudo_title)

        if not correct_district:
            no_match.append((prop_id, address_line, current_district))
            continue

        if correct_district == current_district:
            already_ok.append(prop_id)
            continue

        updates.append((prop_id, address_line, current_district, correct_district))

    # ── Step 3: resolve new location_ids (do this whether committing or not) ─
    resolved = []
    for prop_id, url, old_d, new_d in updates:
        new_loc_id = get_or_create_location(cur, new_d)
        resolved.append((prop_id, url, old_d, new_d, new_loc_id))

    # ── Step 4: print pre-commit summary ──────────────────────────────────
    print(f'\n{"="*70}')
    print('PRE-COMMIT SUMMARY')
    print(f'{"="*70}')
    print(f'  Already correct district : {len(already_ok):4d} properties')
    print(f'  Will be updated          : {len(resolved):4d} properties')
    print(f'  Cannot extract (skipped) : {len(no_match):4d} properties')

    if no_match:
        print(f'\n  Skipped (no URL district found):')
        for pid, url, d in no_match[:10]:
            print(f'    id={pid:5d}  current={d!r:20s}  url={url[:70]}')

    # Count changes by district transition
    from collections import Counter
    transition_counts = Counter(f'{old}->{new}' for _, _, old, new, _ in resolved)
    print(f'\n  District transitions:')
    for trans, cnt in sorted(transition_counts.items(), key=lambda x: -x[1]):
        print(f'    {trans.replace(chr(8594), "->"):40s}: {cnt}')

    print(f'\n  Sample updates (first 20):')
    print(f'  {"id":>6}  {"old district":20}  {"new district":20}  url (truncated)')
    print(f'  {"-"*80}')
    for prop_id, url, old_d, new_d, new_loc_id in resolved[:20]:
        url_short = url[25:75] if len(url) > 75 else url  # trim ikman.lk/en/ad/ prefix
        print(f'  {prop_id:6d}  {old_d:20s}  {new_d:20s}  ...{url_short}')

    print(f'\n{"="*70}')

    if not commit:
        print('DRY RUN — no changes made. Re-run with --commit to apply.')
        cur.close()
        conn.close()
        return

    # ── Step 5: apply updates ─────────────────────────────────────────────
    print(f'Applying {len(resolved)} updates...')
    for prop_id, _, _, _, new_loc_id in resolved:
        cur.execute(
            'UPDATE properties SET location_id=%s WHERE id=%s',
            (new_loc_id, prop_id)
        )
    conn.commit()
    print(f'[OK] Updated {len(resolved)} properties successfully.')

    # ── Step 6: verify — show new district distribution ──────────────────
    cur.execute('''
        SELECT l.district, COUNT(*) cnt
        FROM properties p
        JOIN locations l ON p.location_id = l.id
        WHERE p.address_line LIKE %s
        GROUP BY l.district ORDER BY cnt DESC
    ''', ('%ikman.lk%',))
    print('\nNew district distribution (ikman properties):')
    for district, cnt in cur.fetchall():
        print(f'  {district:25s}: {cnt}')

    cur.close()
    conn.close()


def show_map():
    print(f'\n_SLUG_DISTRICT map ({len(_SLUG_DISTRICT)} entries):')
    print(f'  {"URL slug":40s}  canonical district')
    print(f'  {"-"*60}')
    for slug, district in sorted(_SLUG_DISTRICT.items()):
        print(f'  {slug!r:40s}  {district!r}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fix wrong location_ids for ikman properties')
    parser.add_argument('--commit',   action='store_true', help='Apply changes (default: dry run)')
    parser.add_argument('--show-map', action='store_true', help='Print slug→district map and exit')
    args = parser.parse_args()

    if args.show_map:
        show_map()
    else:
        run(commit=args.commit)
