"""
recommender.py — Phase 5 inference core
=======================================
Loads the trained two-stage artifacts and turns a user profile into ranked
property recommendations with human-readable match reasons.

Used by app.py (the Flask service). Pure-Python, no Flask dependency, so it can
also be imported by the Phase-7 learning job.
"""

import os
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics.pairwise import cosine_similarity

HERE       = os.path.dirname(__file__)
MODEL_PATH = os.path.join(HERE, 'profile_model.joblib')
PROP_PATH  = os.path.join(HERE, 'property_features.joblib')

MATCH_TYPES = ['apartment', 'house', 'room', 'villa']

# Cold-start: profession -> default lifestyle priorities (1-5) when the user
# hasn't ranked them yet.
PROF_DEFAULT_PRIORITIES = {
    'Doctor':              dict(safety=5, price=3, transport=3, hospital=5, space=4),
    'Nurse':               dict(safety=4, price=4, transport=4, hospital=5, space=3),
    'Student':             dict(safety=3, price=5, transport=5, hospital=2, space=2),
    'IT Professional':     dict(safety=3, price=3, transport=4, hospital=2, space=3),
    'Engineer':            dict(safety=3, price=3, transport=3, hospital=3, space=3),
    'Teacher':             dict(safety=4, price=4, transport=4, hospital=3, space=3),
    'Business Owner':      dict(safety=4, price=2, transport=3, hospital=3, space=4),
    'Government Employee': dict(safety=3, price=4, transport=4, hospital=3, space=3),
    'Lawyer':              dict(safety=4, price=3, transport=3, hospital=3, space=3),
    'Other':               dict(safety=3, price=3, transport=3, hospital=3, space=3),
}

_FAMILY_PHRASE = {
    'Single': 'a single occupant', 'Couple': 'a couple',
    'Small Family': 'a family of 3-4', 'Large Family': 'a large family (5+)',
}
_TIER_NAME = {1: 'metro / city-centre', 2: 'regional city', 3: 'suburban / rural'}

_bundle = None
_prop   = None


def load():
    """Lazy-load (and cache) the trained artifacts."""
    global _bundle, _prop
    if _bundle is None:
        _bundle = joblib.load(MODEL_PATH)
        _prop   = joblib.load(PROP_PATH)
    return _bundle, _prop


# ── Profile normalisation + cold start ───────────────────────────────────────
def apply_cold_start(profile: dict) -> dict:
    prof = profile.get('profession') or 'Other'
    defaults = PROF_DEFAULT_PRIORITIES.get(prof, PROF_DEFAULT_PRIORITIES['Other'])

    out = dict(profile)
    for col, dkey in [('priority_safety', 'safety'), ('priority_price', 'price'),
                      ('priority_transport', 'transport'), ('priority_hospital', 'hospital'),
                      ('priority_space', 'space')]:
        v = profile.get(col)
        out[col] = int(v) if v not in (None, '', 0, '0') else defaults[dkey]

    out['profession']     = prof
    out['age_group']      = profile.get('age_group') or '26-35'
    out['family_size']    = profile.get('family_size') or 'Couple'
    out['preferred_type'] = (profile.get('preferred_type')
                             or profile.get('preferred_property_type') or 'apartment')
    out['has_children']   = int(bool(profile.get('has_children')))
    out['has_vehicle']    = int(bool(profile.get('has_vehicle')))
    out['current_district'] = profile.get('current_district') or 'Colombo'
    out['budget'] = float(profile.get('budget')
                          or profile.get('current_rent_budget')
                          or profile.get('max_budget') or 80_000)

    pd_ = profile.get('preferred_districts')
    if isinstance(pd_, str):
        pd_ = [s.strip() for s in pd_.split(',') if s.strip()]
    out['preferred_districts'] = pd_ or []
    return out


# ── STAGE 1: profile -> criteria ─────────────────────────────────────────────
def predict_criteria(bundle, profile: dict) -> dict:
    tier = bundle['district_tier'].get(profile.get('current_district'), 2)
    row = {
        **{c: profile.get(c) for c in bundle['cat_inputs']},
        'budget':             float(profile.get('budget') or 0),
        'has_children':       int(bool(profile.get('has_children'))),
        'has_vehicle':        int(bool(profile.get('has_vehicle'))),
        'current_tier':       tier,
        'priority_safety':    int(profile.get('priority_safety', 3)),
        'priority_price':     int(profile.get('priority_price', 3)),
        'priority_transport': int(profile.get('priority_transport', 3)),
        'priority_hospital':  int(profile.get('priority_hospital', 3)),
        'priority_space':     int(profile.get('priority_space', 3)),
    }
    X = pd.DataFrame([row])[bundle['cat_inputs'] + bundle['num_inputs']]
    Xenc = bundle['preprocessor'].transform(X)

    out = {}
    for t, clf in bundle['classifiers'].items():
        out[t] = clf.predict(Xenc)[0]
    for t, reg in bundle['regressors'].items():
        out[t] = float(reg.predict(Xenc)[0])
    out['matched_district_tier'] = int(out['matched_district_tier'])
    out['min_bedrooms'] = int(round(out['min_bedrooms']))
    # tidy continuous outputs
    for k in ('min_saferent_score', 'transport_score_min', 'hospital_score_min'):
        out[k] = round(out[k], 1)
    out['max_price'] = int(round(out['max_price'], -3))
    return out


# ── STAGE 2: criteria -> properties (priority-weighted similarity) ───────────
# We score each property by how well it SATISFIES the predicted criteria, where
# each dimension is a 0-1 satisfaction ratio (meets/exceeds a minimum -> 1.0;
# within a maximum -> 1.0). The overall match is the cosine similarity of the
# property's weighted satisfaction vector to the "fully-satisfied" ideal vector,
# made magnitude-aware so a uniformly half-satisfied property doesn't look
# perfect. This handles "minimum threshold" semantics that raw-feature cosine
# gets wrong, and degrades gracefully when an exact type/area has no inventory.
EPS = 1e-9


def _w(p):
    """priority rank 1..5 -> dimension weight 0.72 .. 2.0"""
    return 0.4 + 0.32 * float(p)


def _satisfaction_scores(profile, crit, pf, district_tier):
    saf   = pf['saferent_score'].to_numpy(dtype=float)
    hosp  = pf['hospital_score'].to_numpy(dtype=float)
    trans = pf['transport_score'].to_numpy(dtype=float)
    beds  = pf['bedrooms'].to_numpy(dtype=float)
    price = pf['price'].to_numpy(dtype=float)
    ptype = pf['property_type'].to_numpy()
    tier  = pf['district'].map(district_tier).fillna(2).to_numpy(dtype=float)

    s_saf   = np.clip(saf   / max(crit['min_saferent_score'], EPS), 0, 1)
    s_hosp  = np.clip(hosp  / max(crit['hospital_score_min'], EPS), 0, 1)
    s_trans = np.clip(trans / max(crit['transport_score_min'], EPS), 0, 1)
    s_beds  = np.clip(beds  / max(crit['min_bedrooms'], EPS), 0, 1)
    s_price = np.clip(max(crit['max_price'], EPS) / np.maximum(price, EPS), 0, 1)
    s_type  = np.where(ptype == crit['matched_property_type'], 1.0, 0.35)
    s_tier  = 1.0 - np.abs(tier - crit['matched_district_tier']) / 2.0

    # Columns: safety, price, transport, hospital, space(beds), type, tier
    S = np.vstack([s_saf, s_price, s_trans, s_hosp, s_beds, s_type, s_tier]).T
    w = np.array([
        _w(profile['priority_safety']), _w(profile['priority_price']),
        _w(profile['priority_transport']), _w(profile['priority_hospital']),
        _w(profile['priority_space']), 0.7, 0.6,
    ])

    # Weighted cosine to the ideal (all-ones) vector, x magnitude factor.
    Sw    = S * w
    ideal = np.ones(S.shape[1]) * w
    cos   = (Sw @ ideal) / (np.linalg.norm(Sw, axis=1) * np.linalg.norm(ideal) + EPS)
    wmean = Sw.sum(axis=1) / w.sum()                 # weighted mean satisfaction (magnitude)
    return cos * wmean                               # cosine direction x how-satisfied


def recommend(profile: dict, top_k: int = 10) -> dict:
    bundle, prop = load()
    profile = apply_cold_start(profile)
    crit = predict_criteria(bundle, profile)

    pf = prop['properties'].reset_index(drop=True)
    scores = _satisfaction_scores(profile, crit, pf, bundle['district_tier'])

    # Preferred-district boost (kept within [0,1] so match_score reads as a %)
    pref = {d.lower() for d in profile['preferred_districts']}
    if pref:
        boost = np.array([1.08 if str(d).lower() in pref else 1.0 for d in pf['district']])
        scores = scores * boost
    scores = np.clip(scores, 0.0, 1.0)

    order = np.argsort(scores)[::-1][:top_k]
    recs = []
    for idx in order:
        row = pf.iloc[idx]
        recs.append({
            'property_id':     int(row['property_id']),
            'title':           None if pd.isna(row.get('title')) else row.get('title'),
            'district':        row['district'],
            'city':            None if pd.isna(row.get('city')) else row.get('city'),
            'price':           int(row['price']),
            'bedrooms':        int(row['bedrooms']),
            'property_type':   row['property_type'],
            'saferent_score':  round(float(row['saferent_score']), 1),
            'hospital_score':  round(float(row['hospital_score']), 1),
            'transport_score': round(float(row['transport_score']), 1),
            'match_score':     round(float(scores[idx]), 3),
            'match_reasons':   _reasons(row, crit, profile),
        })

    return {
        'recommendations': recs,
        'criteria':        crit,
        'profile_summary': _summary(profile, crit),
    }


# ── Explanations ─────────────────────────────────────────────────────────────
def _reasons(row, crit, profile):
    r = []
    prof, budget = profile['profession'], profile['budget']
    if row['saferent_score'] >= crit['min_saferent_score'] and profile['priority_safety'] >= 4:
        r.append(f"High SafeRent score ({row['saferent_score']:.0f}) matches your safety priority")
    if prof in ('Doctor', 'Nurse') and row['hospital_score'] >= 70:
        r.append("Near hospital facilities — ideal for medical professionals")
    elif row['hospital_score'] >= 75 and profile['priority_hospital'] >= 4:
        r.append("Strong hospital access in this area")
    if row['price'] <= budget:
        r.append(f"Within your LKR {int(budget):,} budget")
    if int(row['bedrooms']) >= crit['min_bedrooms'] and profile['priority_space'] >= 4:
        r.append(f"{int(row['bedrooms'])} bedrooms suit {_FAMILY_PHRASE.get(profile['family_size'], 'your needs')}")
    if str(row['district']).lower() in {d.lower() for d in profile['preferred_districts']}:
        r.append(f"In {row['district']} — one of your preferred districts")
    if row['property_type'] == crit['matched_property_type']:
        r.append(f"{str(row['property_type']).title()} matches your ideal property type")
    if row['transport_score'] >= 75 and profile['priority_transport'] >= 4:
        r.append("Good public transport access")
    if not r:
        r.append("Good overall match to your profile")
    return r[:3]


def _summary(profile, crit):
    fam = _FAMILY_PHRASE.get(profile['family_size'], profile['family_size'])
    prio_label = {
        'priority_safety':   'high-safety areas',
        'priority_hospital': 'proximity to medical facilities',
        'priority_transport':'strong transport access',
        'priority_price':    'budget-friendly options',
        'priority_space':    'spacious homes',
    }
    top2 = sorted(prio_label, key=lambda k: profile[k], reverse=True)[:2]
    focus = ' and '.join(prio_label[k] for k in top2)
    return (f"Based on your profile as a {profile['profession']} with {fam}, "
            f"we prioritised {focus} within a LKR {int(profile['budget']):,} budget.")


def criteria_explanation(crit, profile):
    return [
        f"Ideal property type: {crit['matched_property_type']}",
        f"Target area: tier {crit['matched_district_tier']} ({_TIER_NAME.get(crit['matched_district_tier'], '')})",
        f"Minimum SafeRent score: {crit['min_saferent_score']:.0f}/100",
        f"Maximum price: LKR {int(crit['max_price']):,}",
        f"Minimum bedrooms: {crit['min_bedrooms']}",
        f"Minimum hospital access: {crit['hospital_score_min']:.0f}/100",
        f"Minimum transport access: {crit['transport_score_min']:.0f}/100",
    ]


# ── DB helper (used by /profile-insights and the Phase-7 job) ────────────────
def fetch_user_profile(user_id: int):
    """Read a user's stored preferences and shape them into a profile dict."""
    try:
        import mysql.connector
        c = mysql.connector.connect(host='localhost', port=3306, user='root',
                                    password='', database='smartrentai', charset='utf8mb4')
    except Exception:
        return None
    cur = c.cursor(dictionary=True)
    cur.execute('SELECT * FROM user_preferences WHERE user_id = %s', (user_id,))
    row = cur.fetchone()
    cur.close(); c.close()
    if not row:
        return None
    return {
        'profession':          row.get('profession'),
        'age_group':           row.get('age_group'),
        'family_size':         row.get('family_size'),
        'has_children':        row.get('has_children'),
        'has_vehicle':         row.get('has_vehicle'),
        'current_district':    row.get('current_district'),
        'budget':              row.get('current_rent_budget') or row.get('max_budget'),
        'priority_safety':     row.get('priority_safety'),
        'priority_price':      row.get('priority_price'),
        'priority_transport':  row.get('priority_transport'),
        'priority_hospital':   row.get('priority_hospital'),
        'priority_space':      row.get('priority_space'),
        'preferred_type':      row.get('preferred_property_type') or row.get('property_type'),
        'preferred_districts': row.get('preferred_districts'),
    }
