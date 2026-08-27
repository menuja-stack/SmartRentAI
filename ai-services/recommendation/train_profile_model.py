"""
train_profile_model.py — Phase 4
================================
Two-stage hybrid recommender.

STAGE 1 — Profile -> Criteria (supervised, multi-output)
  Input : user profile vector (profession, age_group, family_size, budget,
          has_children, has_vehicle, current district tier, preferred_type,
          5 lifestyle priorities)
  Output: ideal criteria  -> categorical: matched_property_type, matched_district_tier
                          -> continuous : min_saferent_score, max_price,
                                          min_bedrooms, transport_score_min,
                                          hospital_score_min
  Models: RandomForest (primary)  + XGBoost (comparison)
  Metrics: F1 (macro) for categorical, MAE for continuous

STAGE 2 — Criteria -> Property (cosine similarity)
  Build a scaled property feature matrix in the SAME space as the predicted
  criteria, so the Flask service can cosine-match a user's predicted criteria
  against every live property.

Artifacts:
  profile_model.joblib      (Stage-1 preprocessor + models + metadata)
  property_features.joblib  (Stage-2 property matrix + scaler + layout)

Run:  python train_profile_model.py
"""

import os
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import f1_score, mean_absolute_error, accuracy_score

HERE     = os.path.dirname(__file__)
DATA     = os.path.join(HERE, 'data')
DS_PATH  = os.path.join(DATA, 'profile_property_dataset.csv')
PF_PATH  = os.path.join(DATA, 'property_features.csv')
MODEL_OUT = os.path.join(HERE, 'profile_model.joblib')
PROP_OUT  = os.path.join(HERE, 'property_features.joblib')

# Property price sanity band (LKR/month) — clip scraper outliers (0 / sale prices)
PRICE_MIN, PRICE_MAX = 5_000, 1_500_000

DISTRICT_TIER = {
    'Colombo': 1, 'Gampaha': 1,
    'Kandy': 2, 'Kalutara': 2, 'Galle': 2, 'Kurunegala': 2, 'Matara': 2,
    'Jaffna': 2, 'Anuradhapura': 2, 'Ratnapura': 2, 'Batticaloa': 2,
    'Kegalle': 2, 'Trincomalee': 2, 'Puttalam': 2,
    'Matale': 3, 'Nuwara Eliya': 3, 'Hambantota': 3, 'Kilinochchi': 3,
    'Mannar': 3, 'Mullaitivu': 3, 'Vavuniya': 3, 'Ampara': 3,
    'Polonnaruwa': 3, 'Badulla': 3, 'Monaragala': 3,
}

# Input feature layout
CAT_INPUTS = ['profession', 'age_group', 'family_size', 'preferred_type']
NUM_INPUTS = ['budget', 'has_children', 'has_vehicle', 'current_tier',
              'priority_safety', 'priority_price', 'priority_transport',
              'priority_hospital', 'priority_space']

CLS_TARGETS = ['matched_property_type', 'matched_district_tier']
REG_TARGETS = ['min_saferent_score', 'max_price', 'min_bedrooms',
               'transport_score_min', 'hospital_score_min']

# The shared Stage-2 matching space (property <-> criteria)
MATCH_NUM   = ['price', 'bedrooms', 'saferent_score', 'hospital_score', 'transport_score']
MATCH_TYPES = ['apartment', 'house', 'room', 'villa']
MATCH_COLS  = MATCH_NUM + [f'type_{t}' for t in MATCH_TYPES] + ['district_tier']


def try_xgb():
    try:
        import xgboost  # noqa
        return True
    except Exception:
        return False


# ── STAGE 1 ──────────────────────────────────────────────────────────────────
def train_stage1():
    df = pd.read_csv(DS_PATH)
    df['current_tier'] = df['current_district'].map(DISTRICT_TIER).fillna(2).astype(int)

    X = df[CAT_INPUTS + NUM_INPUTS]
    pre = ColumnTransformer([
        ('cat', OneHotEncoder(handle_unknown='ignore'), CAT_INPUTS),
        ('num', 'passthrough', NUM_INPUTS),
    ])
    Xenc = pre.fit_transform(X)

    y_cls = df[CLS_TARGETS]
    y_reg = df[REG_TARGETS]

    Xtr, Xte, ytr_c, yte_c, ytr_r, yte_r = train_test_split(
        Xenc, y_cls, y_reg, test_size=0.2, random_state=42)

    print('=' * 80)
    print('STAGE 1 — Profile -> Criteria')
    print('=' * 80)
    print(f'Train: {Xtr.shape[0]:,}  Test: {Xte.shape[0]:,}  Features: {Xtr.shape[1]}')

    # ── Classifiers (one per categorical target) ──
    rf_classifiers = {}
    print('\n[RandomForest — categorical targets]  metric: F1 macro / accuracy')
    for t in CLS_TARGETS:
        clf = RandomForestClassifier(n_estimators=200, max_depth=16,
                                     n_jobs=-1, random_state=42, class_weight='balanced')
        clf.fit(Xtr, ytr_c[t])
        pred = clf.predict(Xte)
        f1  = f1_score(yte_c[t], pred, average='macro')
        acc = accuracy_score(yte_c[t], pred)
        print(f'  {t:24s}  F1={f1:.3f}  acc={acc:.3f}')
        rf_classifiers[t] = clf

    # ── Regressors — ONE per target ──
    # (A shared multi-output RF lets max_price's huge variance swamp the score
    #  targets, so we fit an independent RF per continuous target instead.)
    print('\n[RandomForest — continuous targets, one model each]  metric: MAE')
    rf_regressors = {}
    rf_mae = {}
    for t in REG_TARGETS:
        reg = RandomForestRegressor(n_estimators=200, max_depth=18,
                                    n_jobs=-1, random_state=42)
        reg.fit(Xtr, ytr_r[t])
        mae = mean_absolute_error(yte_r[t], reg.predict(Xte))
        rng = yte_r[t].max() - yte_r[t].min()
        rf_mae[t] = mae
        rf_regressors[t] = reg
        print(f'  {t:24s}  MAE={mae:9.1f}  (range {rng:,.0f}, ~{mae/rng*100:4.1f}% of range)')

    # ── XGBoost comparison ──
    if try_xgb():
        from xgboost import XGBClassifier, XGBRegressor
        from sklearn.preprocessing import LabelEncoder
        print('\n[XGBoost — comparison]')
        for t in CLS_TARGETS:
            le = LabelEncoder()
            ytr_enc = le.fit_transform(ytr_c[t])
            yte_enc = le.transform(yte_c[t])
            xgb = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1,
                                subsample=0.9, n_jobs=-1, random_state=42,
                                eval_metric='mlogloss', tree_method='hist')
            xgb.fit(Xtr, ytr_enc)
            f1 = f1_score(yte_enc, xgb.predict(Xte), average='macro')
            print(f'  {t:24s}  F1={f1:.3f}')
        for t in REG_TARGETS:
            xgr = XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.1,
                               subsample=0.9, n_jobs=-1, random_state=42, tree_method='hist')
            xgr.fit(Xtr, ytr_r[t])
            mae = mean_absolute_error(yte_r[t], xgr.predict(Xte))
            tag = 'better' if mae < rf_mae[t] else 'RF wins'
            print(f'  {t:24s}  MAE={mae:9.1f}   ({tag})')
    else:
        print('\n[XGBoost not installed — skipping comparison]')

    # ── Feature importance (per-target — proves priorities drive criteria) ──
    feat_names = (list(pre.named_transformers_['cat'].get_feature_names_out(CAT_INPUTS))
                  + NUM_INPUTS)
    for t in ['min_saferent_score', 'hospital_score_min', 'transport_score_min', 'max_price']:
        imp = pd.Series(rf_regressors[t].feature_importances_, index=feat_names) \
              .sort_values(ascending=False)
        print(f'\n[Top 5 features -> {t}]')
        print(imp.head(5).round(3).to_string())

    bundle = {
        'preprocessor':   pre,
        'classifiers':    rf_classifiers,
        'regressors':     rf_regressors,
        'cat_inputs':     CAT_INPUTS,
        'num_inputs':     NUM_INPUTS,
        'cls_targets':    CLS_TARGETS,
        'reg_targets':    REG_TARGETS,
        'district_tier':  DISTRICT_TIER,
    }
    joblib.dump(bundle, MODEL_OUT)
    print(f'\nSaved Stage-1 model -> {MODEL_OUT}')
    return bundle


# ── STAGE 2 ──────────────────────────────────────────────────────────────────
def build_stage2():
    print('\n' + '=' * 80)
    print('STAGE 2 — Property matrix for cosine matching')
    print('=' * 80)
    pf = pd.read_csv(PF_PATH)

    # Clip price outliers (scraper artifacts) into a sane rental band
    n_out = ((pf['price'] < PRICE_MIN) | (pf['price'] > PRICE_MAX)).sum()
    pf['price'] = pf['price'].clip(PRICE_MIN, PRICE_MAX)
    pf['bedrooms'] = pf['bedrooms'].fillna(0).clip(0, 8)
    pf['district_tier'] = pf['district'].map(DISTRICT_TIER).fillna(2).astype(int)
    for t in MATCH_TYPES:
        pf[f'type_{t}'] = (pf['property_type'] == t).astype(int)

    M = pf[MATCH_COLS].astype(float).values
    scaler = MinMaxScaler()
    Ms = scaler.fit_transform(M)

    joblib.dump({
        'properties':  pf,           # full frame (id, title-less; titles fetched live)
        'matrix':      Ms,           # scaled matching matrix
        'scaler':      scaler,
        'match_cols':  MATCH_COLS,
        'match_num':   MATCH_NUM,
        'match_types': MATCH_TYPES,
        'price_band':  (PRICE_MIN, PRICE_MAX),
    }, PROP_OUT)

    print(f'Properties: {len(pf)}   price outliers clipped: {n_out}')
    print(f'Matching space ({len(MATCH_COLS)} dims): {MATCH_COLS}')
    print(f'Saved Stage-2 matrix -> {PROP_OUT}')
    return pf, Ms, scaler


# ── Demo: full pipeline on one example profile ───────────────────────────────
def demo(bundle, pf, Ms, scaler):
    print('\n' + '=' * 80)
    print('END-TO-END DEMO (Doctor, Small Family, Gampaha, budget 150k)')
    print('=' * 80)
    profile = {
        'profession': 'Doctor', 'age_group': '36-45', 'family_size': 'Small Family',
        'has_children': 1, 'has_vehicle': 1, 'current_district': 'Gampaha', 'budget': 150000,
        'priority_safety': 5, 'priority_price': 3, 'priority_transport': 4,
        'priority_hospital': 5, 'priority_space': 4, 'preferred_type': 'house',
    }
    crit = predict_criteria(bundle, profile)
    print('Predicted ideal criteria:')
    for k, v in crit.items():
        print(f'  {k:24s}: {v}')

    vec = criteria_to_vector(crit, scaler, bundle)
    from sklearn.metrics.pairwise import cosine_similarity
    sims = cosine_similarity([vec], Ms)[0]
    top = np.argsort(sims)[::-1][:10]
    print('\nTop 10 matched properties:')
    for rank, idx in enumerate(top, 1):
        row = pf.iloc[idx]
        print(f'  {rank:2d}. id={int(row.property_id):5d}  score={sims[idx]:.3f}  '
              f'{row.district:12s} {row.property_type:9s} '
              f'beds={int(row.bedrooms)} price={int(row.price):>8,} saferent={row.saferent_score}')


# ── Inference helpers (re-used by the Flask service) ─────────────────────────
def predict_criteria(bundle, profile: dict) -> dict:
    pre  = bundle['preprocessor']
    tier = bundle['district_tier'].get(profile.get('current_district'), 2)
    row = {
        **{c: profile.get(c) for c in bundle['cat_inputs']},
        'budget':            float(profile.get('budget') or 0),
        'has_children':      int(bool(profile.get('has_children'))),
        'has_vehicle':       int(bool(profile.get('has_vehicle'))),
        'current_tier':      tier,
        'priority_safety':   int(profile.get('priority_safety', 3)),
        'priority_price':    int(profile.get('priority_price', 3)),
        'priority_transport':int(profile.get('priority_transport', 3)),
        'priority_hospital': int(profile.get('priority_hospital', 3)),
        'priority_space':    int(profile.get('priority_space', 3)),
    }
    X = pd.DataFrame([row])[bundle['cat_inputs'] + bundle['num_inputs']]
    Xenc = pre.transform(X)
    out = {}
    for t, clf in bundle['classifiers'].items():
        out[t] = clf.predict(Xenc)[0]
    for t, reg in bundle['regressors'].items():
        out[t] = float(reg.predict(Xenc)[0])
    out['matched_district_tier'] = int(out['matched_district_tier'])
    out['min_bedrooms'] = int(round(out['min_bedrooms']))
    return out


def criteria_to_vector(crit: dict, scaler, bundle):
    """Map predicted criteria into the scaled property matching space."""
    num = [crit['max_price'], crit['min_bedrooms'], crit['min_saferent_score'],
           crit['hospital_score_min'], crit['transport_score_min']]
    types = [1.0 if crit['matched_property_type'] == t else 0.0 for t in MATCH_TYPES]
    raw = np.array(num + types + [crit['matched_district_tier']], dtype=float).reshape(1, -1)
    return scaler.transform(raw)[0]


if __name__ == '__main__':
    bundle = train_stage1()
    pf, Ms, scaler = build_stage2()
    demo(bundle, pf, Ms, scaler)
    print('\nDONE. Artifacts: profile_model.joblib, property_features.joblib')
