"""
dedupe_properties.py — remove duplicate property listings.

Cause: portals (house.lk, ikman) re-post the same physical listing under a NEW
listing id / URL, so a later scrape inserts it again. Same agency reference code
in the title + same rent => same listing.

Strategy: group by (title, monthly_rent); keep the OLDEST row (min id); delete the
rest. User saves/reviews on a duplicate are reassigned to the kept row first so
nothing is lost (child rows otherwise CASCADE-delete with the property).

Usage:
    python dedupe_properties.py            # dry run — show what would be removed
    python dedupe_properties.py --commit   # apply
"""

import argparse
import mysql.connector


def get_conn():
    return mysql.connector.connect(host='localhost', port=3306, user='root',
                                   password='', database='smartrentai', charset='utf8mb4')


def run(commit: bool):
    conn = get_conn()
    cur  = conn.cursor(dictionary=True)

    cur.execute('''
        SELECT title, monthly_rent, COUNT(*) cnt, GROUP_CONCAT(id ORDER BY id) ids
        FROM properties
        GROUP BY title, monthly_rent
        HAVING cnt > 1
        ORDER BY cnt DESC
    ''')
    groups = cur.fetchall()

    keep, remove = [], []
    for g in groups:
        ids = [int(x) for x in g['ids'].split(',')]
        keep.append(ids[0])
        remove.extend(ids[1:])

    print(f'Duplicate groups        : {len(groups)}')
    print(f'Rows to keep (oldest)   : {len(keep)}')
    print(f'Redundant rows to delete: {len(remove)}')
    print('\nExamples:')
    for g in groups[:10]:
        ids = [int(x) for x in g['ids'].split(',')]
        print(f"  keep {ids[0]:5d}  delete {ids[1:]}  LKR{g['monthly_rent']:.0f}  {g['title'][:50]}")

    if not remove:
        print('\nNothing to do.')
        cur.close(); conn.close()
        return

    if not commit:
        print('\nDRY RUN — no changes. Re-run with --commit to apply.')
        cur.close(); conn.close()
        return

    wcur = conn.cursor()
    # Map each duplicate -> its keeper, so we can move user data over first
    dup_to_keeper = {}
    for g in groups:
        ids = [int(x) for x in g['ids'].split(',')]
        for d in ids[1:]:
            dup_to_keeper[d] = ids[0]

    moved_saves = moved_reviews = 0
    for dup, keeper in dup_to_keeper.items():
        # Reassign user saves & reviews (UPDATE IGNORE skips would-be duplicates)
        wcur.execute('UPDATE IGNORE saved_properties SET property_id=%s WHERE property_id=%s', (keeper, dup))
        moved_saves += wcur.rowcount
        wcur.execute('UPDATE IGNORE reviews SET property_id=%s WHERE property_id=%s', (keeper, dup))
        moved_reviews += wcur.rowcount

    # Delete the redundant rows (children CASCADE automatically)
    fmt = ','.join(['%s'] * len(remove))
    wcur.execute(f'DELETE FROM properties WHERE id IN ({fmt})', remove)
    deleted = wcur.rowcount
    conn.commit()

    print(f'\n[OK] Reassigned {moved_saves} save(s), {moved_reviews} review(s).')
    print(f'[OK] Deleted {deleted} duplicate properties.')

    wcur.execute('SELECT COUNT(*) FROM properties')
    print(f'Properties remaining: {wcur.fetchone()[0]}')
    wcur.close(); cur.close(); conn.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', action='store_true', help='apply changes (default: dry run)')
    run(ap.parse_args().commit)
