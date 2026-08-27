"""
generate_dataset.py — Phase 2
=============================
Generate a synthetic training dataset that maps USER PROFILES -> IDEAL PROPERTY
CRITERIA for the SmartRentAI "For You" recommender.

We have no historical match data yet, so we encode Sri-Lankan rental-market
domain knowledge (profession / family-size / age-group rules from the spec) into
a generative model. Each row is one (profile -> ideal criteria) example.

Output: data/profile_property_dataset.csv   (10,000 rows)

Run:  python generate_dataset.py
"""

import os
import numpy as np
import pandas as pd

SEED = 42
N_ROWS = 10_000
rng = np.random.default_rng(SEED)

OUT_DIR  = os.path.join(os.path.dirname(__file__), 'data')
OUT_PATH = os.path.join(OUT_DIR, 'profile_property_dataset.csv')

# ── Vocabularies ─────────────────────────────────────────────────────────────
PROFESSIONS = ['Doctor', 'Engineer', 'Teacher', 'Student', 'Business Owner',
               'IT Professional', 'Government Employee', 'Lawyer', 'Nurse', 'Other']
AGE_GROUPS  = ['18-25', '26-35', '36-45', '46-60', '60+']
FAMILY      = ['Single', 'Couple', 'Small Family', 'Large Family']
PROP_TYPES  = ['apartment', 'house', 'room', 'villa']

DISTRICTS = ['Colombo', 'Gampaha', 'Kalutara', 'Kandy', 'Matale', 'Nuwara Eliya',
             'Galle', 'Matara', 'Hambantota', 'Jaffna', 'Kilinochchi', 'Mannar',
             'Mullaitivu', 'Vavuniya', 'Trincomalee', 'Batticaloa', 'Ampara',
             'Kurunegala', 'Puttalam', 'Anuradhapura', 'Polonnaruwa', 'Badulla',
             'Monaragala', 'Ratnapura', 'Kegalle']

# Urban "district tier": 1 = metro, 2 = regional city, 3 = rural
DISTRICT_TIER = {
    'Colombo': 1, 'Gampaha': 1,
    'Kandy': 2, 'Kalutara': 2, 'Galle': 2, 'Kurunegala': 2, 'Matara': 2,
    'Jaffna': 2, 'Anuradhapura': 2, 'Ratnapura': 2, 'Batticaloa': 2,
    'Kegalle': 2, 'Trincomalee': 2, 'Puttalam': 2,
    'Matale': 3, 'Nuwara Eliya': 3, 'Hambantota': 3, 'Kilinochchi': 3,
    'Mannar': 3, 'Mullaitivu': 3, 'Vavuniya': 3, 'Ampara': 3,
    'Polonnaruwa': 3, 'Badulla': 3, 'Monaragala': 3,
}
# Sampling weight for where people currently live (population-ish)
DISTRICT_WEIGHT = np.array([
    18, 12, 6, 7, 2, 2, 4, 3, 2, 3, 1, 1,
    1, 1, 2, 2, 2, 5, 2, 3, 2, 2, 1, 3, 3
], dtype=float)
DISTRICT_WEIGHT /= DISTRICT_WEIGHT.sum()

# Profession -> typical monthly budget range (LKR)
PROF_BUDGET = {
    'Doctor':              (120_000, 300_000),
    'Nurse':              (50_000, 120_000),
    'Engineer':           (80_000, 200_000),
    'IT Professional':    (80_000, 180_000),
    'Teacher':            (40_000, 90_000),
    'Student':            (12_000, 40_000),
    'Business Owner':     (150_000, 400_000),
    'Government Employee':(50_000, 120_000),
    'Lawyer':             (100_000, 250_000),
    'Other':              (40_000, 150_000),
}

# Profession -> age-group sampling weights (keeps profiles coherent)
PROF_AGE_W = {
    'Student':            [0.80, 0.18, 0.02, 0.00, 0.00],
    'Doctor':             [0.02, 0.35, 0.33, 0.25, 0.05],
    'Nurse':              [0.10, 0.40, 0.30, 0.18, 0.02],
    'Engineer':           [0.10, 0.45, 0.28, 0.15, 0.02],
    'IT Professional':    [0.18, 0.50, 0.25, 0.07, 0.00],
    'Teacher':            [0.05, 0.35, 0.32, 0.25, 0.03],
    'Business Owner':     [0.02, 0.25, 0.35, 0.30, 0.08],
    'Government Employee':[0.05, 0.30, 0.33, 0.28, 0.04],
    'Lawyer':             [0.05, 0.35, 0.32, 0.25, 0.03],
    'Other':              [0.15, 0.35, 0.25, 0.20, 0.05],
}

# Profession sampling weights (Students/IT/Teachers common renters)
PROF_W = np.array([6, 9, 9, 14, 5, 12, 10, 5, 7, 8], dtype=float)
PROF_W /= PROF_W.sum()


def clip(x, lo, hi):
    return int(max(lo, min(hi, round(x))))


def derive_criteria(p):
    """Apply domain rules to a sampled profile dict -> ideal criteria dict."""
    prof   = p['profession']
    age    = p['age_group']
    fam    = p['family_size']
    budget = p['budget']
    kids   = p['has_children']
    veh    = p['has_vehicle']

    ps, pp, pt, ph, psp = (p['priority_safety'], p['priority_price'],
                           p['priority_transport'], p['priority_hospital'],
                           p['priority_space'])

    # ── min_bedrooms — driven by family size, nudged by space priority/kids ──
    base_beds = {'Single': 1, 'Couple': 1, 'Small Family': 2, 'Large Family': 3}[fam]
    beds = base_beds + (1 if psp >= 4 else 0) + (1 if (kids and fam in ('Small Family', 'Large Family')) else 0)
    min_bedrooms = clip(beds, 1, 5)

    # ── matched_property_type ───────────────────────────────────────────────
    if fam == 'Large Family':
        ptype = 'villa' if (budget >= 200_000 and rng.random() < 0.4) else 'house'
    elif fam == 'Small Family':
        ptype = 'house' if rng.random() < 0.8 else 'apartment'
    else:  # Single / Couple
        if prof == 'Student' or budget < 35_000:
            ptype = 'room' if rng.random() < 0.6 else 'apartment'
        elif prof in ('IT Professional', 'Engineer') or DISTRICT_TIER[p['current_district']] == 1:
            ptype = 'apartment'
        else:
            ptype = 'apartment' if rng.random() < 0.6 else 'house'
    # Business owners trend to villa/house
    if prof == 'Business Owner' and fam in ('Small Family', 'Large Family') and rng.random() < 0.3:
        ptype = 'villa'

    # ── matched_district_tier (1 metro .. 3 rural) ──────────────────────────
    if prof in ('IT Professional', 'Business Owner', 'Lawyer'):
        tier = 1
    elif prof == 'Student':
        tier = 1 if rng.random() < 0.6 else 2
    elif fam in ('Small Family', 'Large Family'):
        tier = 2
    else:
        tier = DISTRICT_TIER[p['current_district']]
    # Older people prefer quieter (higher tier number) areas
    if age in ('46-60', '60+') and rng.random() < 0.5:
        tier = min(3, tier + 1)
    tier = clip(tier, 1, 3)

    # ── min_saferent_score — safety priority + profession + age ─────────────
    saf = 45 + (ps - 3) * 8
    if prof in ('Doctor', 'Nurse'):
        saf += 12
    if age in ('46-60', '60+'):
        saf += 10
    if fam in ('Small Family', 'Large Family') or kids:
        saf += 6
    min_saferent = clip(saf + rng.normal(0, 3), 30, 95)

    # ── hospital_score_min — medical proximity ──────────────────────────────
    hosp = 40 + (ph - 3) * 8
    if prof in ('Doctor', 'Nurse'):
        hosp += 20
    if age in ('46-60', '60+'):
        hosp += 12
    if kids:
        hosp += 6
    hospital_min = clip(hosp + rng.normal(0, 3), 30, 95)

    # ── transport_score_min — no vehicle / students / IT need transport ─────
    trans = 40 + (pt - 3) * 9
    if not veh:
        trans += 15
    if prof in ('Student', 'IT Professional', 'Teacher', 'Government Employee'):
        trans += 8
    transport_min = clip(trans + rng.normal(0, 3), 25, 95)

    # ── max_price — budget tightened by price sensitivity ───────────────────
    # price priority 5 (very sensitive) -> cap below budget; priority 1 -> allow stretch
    factor = 1.10 - (pp - 1) * 0.06          # pp=1 ->1.10, pp=5 ->0.86
    max_price = int(round(budget * factor, -3))
    max_price = max(10_000, max_price)

    return {
        'matched_property_type': ptype,
        'matched_district_tier': tier,
        'min_saferent_score':    min_saferent,
        'max_price':             max_price,
        'min_bedrooms':          min_bedrooms,
        'transport_score_min':   transport_min,
        'hospital_score_min':    hospital_min,
    }


def sample_profile():
    prof = rng.choice(PROFESSIONS, p=PROF_W)
    age  = rng.choice(AGE_GROUPS, p=PROF_AGE_W[prof])

    # Family size conditioned loosely on age
    if age == '18-25':
        fam = rng.choice(FAMILY, p=[0.55, 0.25, 0.15, 0.05])
    elif age == '26-35':
        fam = rng.choice(FAMILY, p=[0.30, 0.35, 0.25, 0.10])
    elif age == '36-45':
        fam = rng.choice(FAMILY, p=[0.12, 0.23, 0.40, 0.25])
    elif age == '46-60':
        fam = rng.choice(FAMILY, p=[0.12, 0.28, 0.35, 0.25])
    else:  # 60+
        fam = rng.choice(FAMILY, p=[0.25, 0.45, 0.20, 0.10])

    kids = 1 if (fam in ('Small Family', 'Large Family') and rng.random() < 0.85) \
                or (fam == 'Couple' and rng.random() < 0.15) else 0
    veh  = 1 if rng.random() < (0.35 if prof == 'Student' else 0.65) else 0

    cur_district = rng.choice(DISTRICTS, p=DISTRICT_WEIGHT)

    lo, hi = PROF_BUDGET[prof]
    budget = int(rng.uniform(lo, hi))
    if age == '18-25':
        budget = min(budget, 45_000)        # young renters cap
    budget = int(round(budget, -3))

    # Lifestyle priority ranks 1..5 — base means by profession, then noise
    def rank(mean):
        return clip(rng.normal(mean, 1.1), 1, 5)

    safety_mean = 4.2 if (prof in ('Doctor', 'Nurse') or age in ('46-60', '60+')) else 3.1
    price_mean  = 4.3 if prof in ('Student', 'Teacher', 'Government Employee') else 2.8
    trans_mean  = 4.2 if (prof in ('Student', 'IT Professional') or veh == 0) else 2.9
    hosp_mean   = 4.4 if (prof in ('Doctor', 'Nurse') or age in ('46-60', '60+') or kids) else 2.6
    space_mean  = 4.2 if fam in ('Small Family', 'Large Family') else 2.6

    # preferred_type — what the user *says* they want (noisy vs the ideal)
    if fam in ('Small Family', 'Large Family'):
        ptype_pref = rng.choice(PROP_TYPES, p=[0.20, 0.62, 0.05, 0.13])
    elif prof == 'Student':
        ptype_pref = rng.choice(PROP_TYPES, p=[0.35, 0.05, 0.58, 0.02])
    else:
        ptype_pref = rng.choice(PROP_TYPES, p=[0.60, 0.22, 0.13, 0.05])

    return {
        'profession': prof, 'age_group': age, 'family_size': fam,
        'has_children': kids, 'has_vehicle': veh,
        'current_district': cur_district, 'budget': budget,
        'priority_safety': rank(safety_mean), 'priority_price': rank(price_mean),
        'priority_transport': rank(trans_mean), 'priority_hospital': rank(hosp_mean),
        'priority_space': rank(space_mean),
        'preferred_type': ptype_pref,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    for _ in range(N_ROWS):
        prof = sample_profile()
        crit = derive_criteria(prof)
        rows.append({**prof, **crit})

    df = pd.DataFrame(rows)
    col_order = [
        'profession', 'age_group', 'family_size', 'has_children', 'has_vehicle',
        'current_district', 'budget',
        'priority_safety', 'priority_price', 'priority_transport',
        'priority_hospital', 'priority_space', 'preferred_type',
        'matched_property_type', 'matched_district_tier', 'min_saferent_score',
        'max_price', 'min_bedrooms', 'transport_score_min', 'hospital_score_min',
    ]
    df = df[col_order]
    df.to_csv(OUT_PATH, index=False)

    # ── Report ──────────────────────────────────────────────────────────────
    print(f'Saved {len(df):,} rows -> {OUT_PATH}')
    print(f'Columns ({len(df.columns)}): {list(df.columns)}')
    print('\n' + '=' * 80)
    print('FIRST 20 ROWS')
    print('=' * 80)
    with pd.option_context('display.max_columns', None, 'display.width', 200):
        print(df.head(20).to_string(index=False))

    print('\n' + '=' * 80)
    print('VALUE DISTRIBUTIONS')
    print('=' * 80)
    for c in ['profession', 'age_group', 'family_size', 'preferred_type',
              'matched_property_type', 'matched_district_tier', 'min_bedrooms',
              'has_children', 'has_vehicle']:
        print(f'\n[{c}]')
        print(df[c].value_counts().sort_index().to_string())

    print('\n[numeric summaries]')
    print(df[['budget', 'max_price', 'min_saferent_score', 'hospital_score_min',
              'transport_score_min', 'priority_safety', 'priority_price',
              'priority_transport', 'priority_hospital', 'priority_space']]
          .describe().round(1).to_string())

    # Sanity: a couple of rule checks
    print('\n' + '=' * 80)
    print('RULE SANITY CHECKS')
    print('=' * 80)
    doc = df[df.profession.isin(['Doctor', 'Nurse'])]
    print(f"Doctors/Nurses avg hospital_score_min : {doc.hospital_score_min.mean():.1f}  (overall {df.hospital_score_min.mean():.1f})")
    stu = df[df.profession == 'Student']
    print(f"Students avg budget                   : {stu.budget.mean():,.0f}  (overall {df.budget.mean():,.0f})")
    print(f"Students % room/apartment matched     : {(stu.matched_property_type.isin(['room','apartment'])).mean()*100:.0f}%")
    lf = df[df.family_size == 'Large Family']
    print(f"Large Family avg min_bedrooms         : {lf.min_bedrooms.mean():.2f}  (overall {df.min_bedrooms.mean():.2f})")
    older = df[df.age_group.isin(['46-60', '60+'])]
    print(f"Age 46+ avg min_saferent_score        : {older.min_saferent_score.mean():.1f}  (overall {df.min_saferent_score.mean():.1f})")


if __name__ == '__main__':
    main()
