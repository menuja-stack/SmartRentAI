"""
update_preferences.py — Phase 7
===============================
Closes the feedback loop. Reads implicit signals (view / save / enquiry) logged
to search_history and re-weights each user's lifestyle priority scores in
user_preferences.

Idea: if a user keeps saving high-SafeRent properties, raise priority_safety;
if they gravitate to cheap listings, raise priority_price; etc. Stronger actions
count more (view=1, save=3, enquiry=5). The learned rank is blended 50/50 with
the user's existing priority so it adapts gradually.

Run:
    python update_preferences.py                 # learn for all users w/ enough signals
    python update_preferences.py --commit         # actually write the new priorities
    python update_preferences.py --user 3         # only this user
    python update_preferences.py --seed-demo 3    # inject sample signals for user 3 (demo)

Designed to run on demand or from a daily cron.
"""

import os
import argparse
import numpy as np
import pandas as pd

ACTION_WEIGHT = {'view': 1.0, 'save': 3.0, 'enquiry': 5.0}
MIN_SIGNALS   = 2          # min distinct interacted properties to learn from
BLEND         = 0.5        # weight of the learned rank vs the existing priority
PRICE_BAND    = (5_000, 1_500_000)

HERE = os.path.dirname(__file__)
FEATURES_CSV = os.path.join(HERE, 'data', 'property_features.csv')


def get_conn():
    import mysql.connector
    return mysql.connector.connect(host='localhost', port=3306, user='root',
                                   password='', database='smartrentai', charset='utf8mb4')


def load_features():
    df = pd.read_csv(FEATURES_CSV).set_index('property_id')
    df['price'] = pd.to_numeric(df['price'], errors='coerce').clip(*PRICE_BAND)
    df['bedrooms'] = pd.to_numeric(df['bedrooms'], errors='coerce').fillna(0)
    return df


def pct_of(series, value):
    """Fraction of the population <= value (a percentile in [0,1])."""
    s = series.dropna().values
    if len(s) == 0 or pd.isna(value):
        return 0.5
    return float((s <= value).mean())


def rank_from_pct(p):
    """percentile 0..1 -> priority rank 1..5"""
    return int(np.clip(round(1 + 4 * p), 1, 5))


def learn_for_user(cur, feats, user_id):
    cur.execute(
        "SELECT property_id, action FROM search_history "
        "WHERE user_id=%s AND action IN ('view','save','enquiry') AND property_id IS NOT NULL",
        (user_id,))
    rows = cur.fetchall()
    if not rows:
        return None

    # Aggregate action weight per property
    wsum = {}
    for pid, action in rows:
        if pid in feats.index:
            wsum[pid] = wsum.get(pid, 0.0) + ACTION_WEIGHT.get(action, 1.0)
    if len(wsum) < MIN_SIGNALS:
        return None

    pids = list(wsum.keys())
    w    = np.array([wsum[p] for p in pids])
    sub  = feats.loc[pids]

    def wmean(col):
        return float(np.average(sub[col].values, weights=w))

    signal = {
        'saferent':  wmean('saferent_score'),
        'hospital':  wmean('hospital_score'),
        'transport': wmean('transport_score'),
        'price':     wmean('price'),
        'bedrooms':  wmean('bedrooms'),
    }

    # Percentile of the user's weighted signal within the population
    target = {
        'priority_safety':    rank_from_pct(pct_of(feats['saferent_score'],  signal['saferent'])),
        'priority_hospital':  rank_from_pct(pct_of(feats['hospital_score'],  signal['hospital'])),
        'priority_transport': rank_from_pct(pct_of(feats['transport_score'], signal['transport'])),
        'priority_space':     rank_from_pct(pct_of(feats['bedrooms'],        signal['bedrooms'])),
        # cheaper interactions => more price-sensitive => higher priority_price
        'priority_price':     rank_from_pct(1 - pct_of(feats['price'],       signal['price'])),
    }

    # Current priorities
    cur.execute(
        "SELECT priority_safety, priority_price, priority_transport, priority_hospital, priority_space "
        "FROM user_preferences WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if not row:
        return None
    current = dict(zip(['priority_safety', 'priority_price', 'priority_transport',
                        'priority_hospital', 'priority_space'], row))

    learned = {}
    for k, tgt in target.items():
        old = current[k] if current[k] is not None else 3
        learned[k] = int(np.clip(round((1 - BLEND) * old + BLEND * tgt), 1, 5))

    return {
        'user_id': user_id, 'n_props': len(wsum), 'n_signals': int(w.sum()),
        'signal': signal, 'target': target, 'current': current, 'learned': learned,
    }


def seed_demo(cur, user_id, feats):
    """
    Self-contained demo: reset the user's priorities to neutral (3) and clear old
    signals, then inject interactions with the highest hospital+transport-access
    properties — so the learning job should visibly raise priority_hospital and
    priority_transport.
    """
    cur.execute("DELETE FROM search_history WHERE user_id=%s "
                "AND action IN ('view','save','enquiry')", (user_id,))
    cur.execute("UPDATE user_preferences SET priority_safety=3, priority_price=3, "
                "priority_transport=3, priority_hospital=3, priority_space=3, "
                "priorities_learned=0 WHERE user_id=%s", (user_id,))

    top = feats.sort_values(['hospital_score', 'transport_score'], ascending=False).head(4)
    inserts = []
    for i, pid in enumerate(top.index):
        action = 'enquiry' if i == 0 else 'save'
        inserts.append((user_id, f'{action}:{pid}', int(pid), action))
    for pid in top.index[:2]:
        inserts.append((user_id, f'view:{pid}', int(pid), 'view'))
    cur.executemany(
        'INSERT INTO search_history (user_id, query, property_id, action) VALUES (%s,%s,%s,%s)',
        inserts)
    print(f'[seed-demo] reset user {user_id} priorities to 3/3/3/3/3 and inserted '
          f'{len(inserts)} signals on highest hospital+transport properties.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', action='store_true', help='write new priorities (default: dry run)')
    ap.add_argument('--user', type=int, help='only learn for this user id')
    ap.add_argument('--seed-demo', type=int, metavar='USER_ID', help='inject demo signals for a user')
    args = ap.parse_args()

    feats = load_features()
    conn  = get_conn()
    cur   = conn.cursor()

    if args.seed_demo:
        seed_demo(cur, args.seed_demo, feats)
        conn.commit()

    # Which users to process
    if args.user:
        user_ids = [args.user]
    else:
        cur.execute("SELECT DISTINCT user_id FROM search_history "
                    "WHERE action IN ('view','save','enquiry') AND property_id IS NOT NULL")
        user_ids = [r[0] for r in cur.fetchall()]

    print(f'\nUsers with implicit feedback: {len(user_ids)}')
    updated = 0
    for uid in user_ids:
        res = learn_for_user(cur, feats, uid)
        if not res:
            continue
        print(f'\n=== user {uid}  ({res["n_props"]} properties, weighted signal {res["n_signals"]:.0f}) ===')
        print('  weighted signal means: ' + ', '.join(
            f'{k}={v:,.0f}' if k == 'price' else f'{k}={v:.0f}' for k, v in res['signal'].items()))
        print(f'  {"priority":20s} {"old":>4s} {"->":>2s} {"new":>4s}   (learned target)')
        changed = False
        for k in ['priority_safety', 'priority_price', 'priority_transport', 'priority_hospital', 'priority_space']:
            old, new, tgt = res['current'][k], res['learned'][k], res['target'][k]
            mark = '' if old == new else '  <-- changed'
            if old != new:
                changed = True
            print(f'  {k:20s} {str(old):>4s} -> {str(new):>4s}        (target {tgt}){mark}')

        if args.commit and changed:
            cur.execute(
                "UPDATE user_preferences SET priority_safety=%s, priority_price=%s, "
                "priority_transport=%s, priority_hospital=%s, priority_space=%s, "
                "priorities_learned=1 WHERE user_id=%s",
                (res['learned']['priority_safety'], res['learned']['priority_price'],
                 res['learned']['priority_transport'], res['learned']['priority_hospital'],
                 res['learned']['priority_space'], uid))
            updated += 1

    if args.commit:
        conn.commit()
        print(f'\n[OK] Committed learned priorities for {updated} user(s).')
    else:
        print('\nDRY RUN - no changes written. Re-run with --commit to apply.')

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
