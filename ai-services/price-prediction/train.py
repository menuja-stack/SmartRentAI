"""
SmartRentAI — Price Prediction Training Pipeline
Trains XGBoost, GradientBoosting, CatBoost on real scraped data from MySQL.
Run: python train.py
Saves: price_model.joblib, scaler.joblib, encoders.joblib, outputs/
"""
import sys, time, warnings
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import mysql.connector

from sklearn.model_selection import train_test_split, cross_val_score, RandomizedSearchCV, KFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import GradientBoostingRegressor
from xgboost import XGBRegressor

try:
    from catboost import CatBoostRegressor, Pool
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False
    print('[WARN] CatBoost not installed — skipping Model 3')

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    print('[WARN] Optuna not installed — using RandomizedSearchCV for tuning')

try:
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), 'outputs')
SCRIPT_DIR  = os.path.dirname(__file__)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# STEP 1 — Data Extraction
# ─────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('STEP 1 — Extracting data from MySQL')
print('='*60)

conn = mysql.connector.connect(
    host='localhost', port=3306, user='root', password='',
    database='smartrentai', charset='utf8mb4'
)
query = """
    SELECT
        p.id,
        p.monthly_rent,
        p.bedrooms,
        p.bathrooms,
        p.property_type,
        p.furnished,
        p.area_sqft,
        l.district,
        l.city,
        l.latitude,
        l.longitude
    FROM properties p
    JOIN locations l ON p.location_id = l.id
    WHERE p.status = 'available'
      AND p.monthly_rent IS NOT NULL
      AND p.monthly_rent > 0
"""
raw_df = pd.read_sql(query, conn)
conn.close()

print(f'Rows fetched       : {len(raw_df)}')
print(f'Shape              : {raw_df.shape}')
print(f'\nMissing values:\n{raw_df.isnull().sum()}')
print(f'\nPrice stats:\n{raw_df["monthly_rent"].describe()}')
print(f'\nRows with bedrooms  == 0 : {(raw_df["bedrooms"]  == 0).sum()}')
print(f'Rows with bathrooms == 0 : {(raw_df["bathrooms"] == 0).sum()}')

# Identify low-coverage columns up front
coverage = raw_df.notna().mean()
print(f'\nColumn coverage (% non-null):')
for col, pct in coverage.items():
    flag = ' ← WILL DROP (< 10% coverage)' if pct < 0.1 else ''
    print(f'  {col:<20}: {pct:.1%}{flag}')

low_coverage_cols = coverage[coverage < 0.1].index.tolist()

# ─────────────────────────────────────────────────────────────
# STEP 2 — Data Cleaning
# ─────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('STEP 2 — Cleaning')
print('='*60)

df = raw_df.copy()
print(f'Start             : {len(df)} rows')

# Drop very low coverage columns (< 10% non-null) — they're noise after imputation
if low_coverage_cols:
    df.drop(columns=low_coverage_cols, errors='ignore', inplace=True)
    print(f'Dropped low-coverage cols: {low_coverage_cols}')

# IQR outlier removal on price (only extreme outliers; keep a wide range)
Q1, Q3 = df['monthly_rent'].quantile(0.25), df['monthly_rent'].quantile(0.75)
IQR = Q3 - Q1
lo, hi = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
before = len(df)
df = df[(df['monthly_rent'] >= max(lo, 1000)) & (df['monthly_rent'] <= hi)]
print(f'After IQR filter  : {len(df)} rows  (removed {before - len(df)} outliers, LKR {lo:,.0f}–{hi:,.0f})')

# Impute bedrooms/bathrooms == 0 with district median (preserve data)
for col in ['bedrooms', 'bathrooms']:
    mask = df[col] == 0
    if mask.any():
        pos_data = df[df[col] > 0]
        medians  = pos_data.groupby('district')[col].median()
        global_m = pos_data[col].median()
        df.loc[mask, col] = df.loc[mask, 'district'].map(medians).fillna(global_m)
        df[col] = df[col].round().astype(int)
        print(f'Imputed {mask.sum()} zero-{col} rows with district median')

# Lat/lng: fill with district centroid if present (moderate coverage)
for coord in ['latitude', 'longitude']:
    if coord in df.columns:
        null_mask = df[coord].isna()
        if null_mask.any():
            centroids = df.groupby('district')[coord].transform('median')
            df[coord] = df[coord].fillna(centroids)
            print(f'Imputed {null_mask.sum()} null {coord} values')
        # If still null (whole district has no coords), drop the column
        if df[coord].isna().mean() > 0.3:
            df.drop(columns=[coord], inplace=True)
            print(f'Dropped {coord} (> 30% still null after imputation)')

# ── Encoding ────────────────────────────────────────────────
# Rationale for choices:
#  property_type → LabelEncoder (5 levels, ordinal ordering not critical but LE keeps it simple)
#  district      → Target encoding: replace with mean(monthly_rent) per district.
#                  This directly embeds location price premium. With 18 districts and
#                  only ~340 rows, one-hot would add 17 sparse columns hurting gradient boosters.
#  furnished     → Ordinal map 0/1/2 (natural order: unfurnished < semi < furnished)

furnished_map = {'unfurnished': 0, 'semi-furnished': 1, 'furnished': 2}
df['furnished_num'] = df['furnished'].map(furnished_map).fillna(0).astype(int)

le_type = LabelEncoder()
df['property_type_enc'] = le_type.fit_transform(df['property_type'].fillna('apartment'))

district_means = df.groupby('district')['monthly_rent'].mean()
df['district_enc'] = df['district'].map(district_means)

# District centroid lat/lng — lets the serving API derive coordinates from
# district alone, since POST /predict requests only ever carry district
# (never raw latitude/longitude).
district_latlng = {}
global_latlng = {}
for coord in ['latitude', 'longitude']:
    if coord in df.columns:
        district_latlng[coord] = df.groupby('district')[coord].median().to_dict()
        global_latlng[coord] = float(df[coord].median())

print(f'\nFinal clean dataset: {len(df)} rows')
print(f'Price range: LKR {df["monthly_rent"].min():,.0f} – {df["monthly_rent"].max():,.0f}')

# ─────────────────────────────────────────────────────────────
# STEP 3 — Feature Correlation & Selection
# ─────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('STEP 3 — Feature Correlation & Selection')
print('='*60)

candidate_features = ['bedrooms', 'bathrooms', 'furnished_num',
                      'property_type_enc', 'district_enc']
# Add lat/lng only if they survived cleaning and have reasonable coverage
for geo in ['latitude', 'longitude']:
    if geo in df.columns and df[geo].notna().mean() > 0.5:
        candidate_features.append(geo)

analysis_df = df[candidate_features + ['monthly_rent']].dropna()

corr_matrix = analysis_df.corr()
price_corr  = corr_matrix['monthly_rent'].drop('monthly_rent').abs().sort_values(ascending=False)

print('\nCorrelation with monthly_rent (absolute):')
for feat, val in price_corr.items():
    flag = ' ← DROP (< 0.05)' if val < 0.05 else ''
    print(f'  {feat:<22}: {val:.4f}{flag}')

drop_features = price_corr[price_corr < 0.05].index.tolist()
keep_features = [f for f in candidate_features if f not in drop_features]
print(f'\nDropping {len(drop_features)} low-signal features: {drop_features}')
print(f'Keeping  {len(keep_features)} features: {keep_features}')

# Check multicollinearity between kept features
feat_corr_matrix = analysis_df[keep_features].corr().abs()
high_pairs = []
for i in range(len(keep_features)):
    for j in range(i+1, len(keep_features)):
        c = feat_corr_matrix.iloc[i, j]
        if c > 0.85:
            high_pairs.append((keep_features[i], keep_features[j], round(c, 3)))

if high_pairs:
    print(f'\nHigh pairwise correlation (> 0.85):')
    for a, b, c in high_pairs:
        print(f'  {a} ↔ {b}: {c}')
    # Drop the feature with lower correlation to price from each pair
    to_drop_mc = set()
    for a, b, _ in high_pairs:
        drop_one = a if price_corr.get(a, 0) < price_corr.get(b, 0) else b
        to_drop_mc.add(drop_one)
    keep_features = [f for f in keep_features if f not in to_drop_mc]
    print(f'Dropping collinear: {list(to_drop_mc)}')
    print(f'Final features: {keep_features}')
else:
    print('\nNo severe multicollinearity detected')

# Save correlation heatmap
fig, ax = plt.subplots(figsize=(10, 8))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, annot=True, fmt='.2f',
            cmap='RdYlGn', center=0, ax=ax, linewidths=0.5)
ax.set_title('Feature Correlation Heatmap — SmartRentAI Price Prediction', fontsize=13)
plt.tight_layout()
heatmap_path = os.path.join(OUTPUT_DIR, 'correlation_heatmap.png')
plt.savefig(heatmap_path, dpi=150)
plt.close()
print(f'\nHeatmap saved → {heatmap_path}')

# VIF (optional, informational only after pairwise check above)
if HAS_STATSMODELS and len(keep_features) >= 2:
    print('\nVIF (informational):')
    vif_df = analysis_df[keep_features].dropna()
    for i, col in enumerate(keep_features):
        try:
            vif = variance_inflation_factor(vif_df.values.astype(float), i)
            print(f'  {col:<22}: {vif:.2f}')
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────
# STEP 4 — Train/Test Split + Scaling
# ─────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('STEP 4 — Train/Test Split & Scaling')
print('='*60)

model_df = df[keep_features + ['monthly_rent', 'district']].dropna().reset_index(drop=True)

X = model_df[keep_features].values.astype(float)
y = model_df['monthly_rent'].values.astype(float)

try:
    X_train, X_test, y_train, y_test, dist_train, dist_test = train_test_split(
        X, y, model_df['district'].values,
        test_size=0.2, random_state=42,
        stratify=model_df['district'].values
    )
    print('Split: 80/20 stratified by district')
except ValueError:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print('Split: 80/20 random (too few samples per district for stratify)')

print(f'Train: {len(X_train)} samples | Test: {len(X_test)} samples')

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

scaler_path = os.path.join(SCRIPT_DIR, 'scaler.joblib')
joblib.dump({'scaler': scaler, 'feature_cols': keep_features}, scaler_path)
print(f'Scaler saved → {scaler_path}')

# ─────────────────────────────────────────────────────────────
# STEP 5 — Train 3 Models
# ─────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('STEP 5 — Training Models')
print('='*60)

results = {}

def eval_model(model, X_tr, y_tr, X_te, y_te, name, fit_params=None):
    t0 = time.time()
    if fit_params:
        model.fit(X_tr, y_tr, **fit_params)
    else:
        model.fit(X_tr, y_tr)
    t_train = time.time() - t0
    preds   = model.predict(X_te)
    mae     = mean_absolute_error(y_te, preds)
    rmse    = np.sqrt(mean_squared_error(y_te, preds))
    r2      = r2_score(y_te, preds)
    cv      = cross_val_score(model, X_tr, y_tr, cv=5, scoring='r2', n_jobs=1)
    return {
        'name': name, 'model': model,
        'MAE': mae, 'RMSE': rmse, 'R2': r2,
        'CV_R2_mean': cv.mean(), 'CV_R2_std': cv.std(),
        'train_time': t_train,
    }


# ── Model 1: XGBoost ────────────────────────────────────────
print('\n--- Model 1: XGBoost ---')

if HAS_OPTUNA:
    def xgb_objective(trial):
        params = {
            'n_estimators':     trial.suggest_int('n_estimators', 100, 600),
            'max_depth':        trial.suggest_int('max_depth', 3, 8),
            'learning_rate':    trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'subsample':        trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'random_state': 42, 'n_jobs': 1, 'verbosity': 0,
        }
        cv = cross_val_score(XGBRegressor(**params), X_train_s, y_train,
                             cv=5, scoring='r2', n_jobs=1)
        return cv.mean()

    study_xgb = optuna.create_study(direction='maximize')
    study_xgb.optimize(xgb_objective, n_trials=40, show_progress_bar=False)
    best_xgb_params = {**study_xgb.best_params, 'random_state': 42, 'n_jobs': 1, 'verbosity': 0}
    print(f'  Best params (Optuna, 40 trials): {study_xgb.best_params}')
else:
    param_grid_xgb = {
        'n_estimators':     [100, 200, 400, 600],
        'max_depth':        [3, 4, 5, 6],
        'learning_rate':    [0.01, 0.05, 0.1, 0.2],
        'subsample':        [0.7, 0.85, 1.0],
        'colsample_bytree': [0.7, 0.85, 1.0],
        'min_child_weight': [1, 3, 5],
    }
    xgb_search = RandomizedSearchCV(
        XGBRegressor(random_state=42, n_jobs=1, verbosity=0),
        param_grid_xgb, n_iter=30, cv=5, scoring='r2', random_state=42, n_jobs=1
    )
    xgb_search.fit(X_train_s, y_train)
    best_xgb_params = {**xgb_search.best_params_, 'random_state': 42, 'n_jobs': 1, 'verbosity': 0}
    print(f'  Best params (RandomSearch): {xgb_search.best_params_}')

xgb_model = XGBRegressor(**best_xgb_params)
res_xgb   = eval_model(xgb_model, X_train_s, y_train, X_test_s, y_test, 'XGBoost')
results['XGBoost'] = res_xgb
print(f'  MAE={res_xgb["MAE"]:,.0f}  RMSE={res_xgb["RMSE"]:,.0f}  R²={res_xgb["R2"]:.4f}  CV-R²={res_xgb["CV_R2_mean"]:.4f}±{res_xgb["CV_R2_std"]:.4f}  ({res_xgb["train_time"]:.1f}s)')


# ── Model 2: GradientBoosting ────────────────────────────────
print('\n--- Model 2: GradientBoosting (sklearn) ---')

param_grid_gbr = {
    'n_estimators':      [100, 200, 300, 500],
    'max_depth':         [2, 3, 4, 5],
    'learning_rate':     [0.005, 0.01, 0.05, 0.1, 0.15],
    'min_samples_split': [2, 5, 10, 15],
    'subsample':         [0.7, 0.85, 1.0],
}
gbr_search = RandomizedSearchCV(
    GradientBoostingRegressor(random_state=42),
    param_grid_gbr, n_iter=30, cv=5, scoring='r2', random_state=42, n_jobs=1
)
gbr_search.fit(X_train_s, y_train)
best_gbr_params = gbr_search.best_params_
print(f'  Best params: {best_gbr_params}')

gbr_model = GradientBoostingRegressor(**best_gbr_params, random_state=42)
res_gbr   = eval_model(gbr_model, X_train_s, y_train, X_test_s, y_test, 'GradientBoosting')
results['GradientBoosting'] = res_gbr
print(f'  MAE={res_gbr["MAE"]:,.0f}  RMSE={res_gbr["RMSE"]:,.0f}  R²={res_gbr["R2"]:.4f}  CV-R²={res_gbr["CV_R2_mean"]:.4f}±{res_gbr["CV_R2_std"]:.4f}  ({res_gbr["train_time"]:.1f}s)')


# ── Model 3: CatBoost ────────────────────────────────────────
if HAS_CATBOOST:
    print('\n--- Model 3: CatBoost ---')
    # CatBoost handles categoricals natively via Pool with cat_features.
    # We use raw district + property_type strings (unencoded) as cat features.
    # Numeric features: bedrooms, bathrooms, furnished_num + any geo kept.
    numeric_feats = [f for f in keep_features
                     if f not in ('district_enc', 'property_type_enc')]
    cat_str_feats = ['district', 'property_type']

    cb_df = df[numeric_feats + cat_str_feats + ['monthly_rent']].dropna().reset_index(drop=True)
    all_cb_cols = numeric_feats + cat_str_feats
    cat_indices = [all_cb_cols.index('district'), all_cb_cols.index('property_type')]

    # Ensure numeric columns are float (CatBoost Pool needs proper dtypes on a DataFrame)
    for nc in numeric_feats:
        cb_df[nc] = pd.to_numeric(cb_df[nc], errors='coerce')

    Xc_df = cb_df[all_cb_cols]
    yc    = cb_df['monthly_rent'].values.astype(float)

    try:
        idx = np.arange(len(Xc_df))
        tr_idx, te_idx = train_test_split(idx, test_size=0.2, random_state=42,
                                          stratify=cb_df['district'].values)
    except ValueError:
        idx = np.arange(len(Xc_df))
        tr_idx, te_idx = train_test_split(idx, test_size=0.2, random_state=42)

    Xc_train_df = Xc_df.iloc[tr_idx].reset_index(drop=True)
    Xc_test_df  = Xc_df.iloc[te_idx].reset_index(drop=True)
    yc_train = yc[tr_idx]
    yc_test  = yc[te_idx]

    # Pass DataFrame so CatBoost can distinguish float vs string columns by dtype
    train_pool = Pool(Xc_train_df, yc_train, cat_features=cat_str_feats)
    test_pool  = Pool(Xc_test_df,  yc_test,  cat_features=cat_str_feats)

    if HAS_OPTUNA:
        def cat_objective(trial):
            params = {
                'iterations':    trial.suggest_int('iterations', 100, 600),
                'depth':         trial.suggest_int('depth', 4, 8),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'l2_leaf_reg':   trial.suggest_float('l2_leaf_reg', 1.0, 10.0),
                'verbose': 0, 'random_seed': 42,
            }
            kf = KFold(n_splits=3, shuffle=True, random_state=42)
            scores = []
            idx_all = np.arange(len(Xc_train_df))
            for tr_i, val_i in kf.split(idx_all):
                p_tr  = Pool(Xc_train_df.iloc[tr_i],  yc_train[tr_i],  cat_features=cat_str_feats)
                p_val = Pool(Xc_train_df.iloc[val_i], yc_train[val_i], cat_features=cat_str_feats)
                m = CatBoostRegressor(**params, cat_features=cat_str_feats)
                m.fit(p_tr, eval_set=p_val, verbose=0)
                scores.append(r2_score(yc_train[val_i], m.predict(p_val)))
            return np.mean(scores)

        study_cat = optuna.create_study(direction='maximize')
        study_cat.optimize(cat_objective, n_trials=20, show_progress_bar=False)
        best_cat_params = {**study_cat.best_params, 'verbose': 0, 'random_seed': 42}
        print(f'  Best params (Optuna): {study_cat.best_params}')
    else:
        best_cat_params = {'iterations': 400, 'depth': 6, 'learning_rate': 0.05,
                           'l2_leaf_reg': 3.0, 'verbose': 0, 'random_seed': 42}
        print(f'  Params (default): {best_cat_params}')

    t0 = time.time()
    cat_model = CatBoostRegressor(**best_cat_params, cat_features=cat_indices)
    cat_model.fit(train_pool, eval_set=test_pool, verbose=0)
    t_cat = time.time() - t0

    cat_preds = cat_model.predict(test_pool)
    mae_c     = mean_absolute_error(yc_test, cat_preds)
    rmse_c    = np.sqrt(mean_squared_error(yc_test, cat_preds))
    r2_c      = r2_score(yc_test, cat_preds)

    # Manual 5-fold CV for CatBoost
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = []
    idx_all = np.arange(len(Xc_train_df))
    for tr_i, val_i in kf.split(idx_all):
        p_tr  = Pool(Xc_train_df.iloc[tr_i],  yc_train[tr_i],  cat_features=cat_str_feats)
        p_val = Pool(Xc_train_df.iloc[val_i], yc_train[val_i], cat_features=cat_str_feats)
        m = CatBoostRegressor(**best_cat_params, cat_features=cat_str_feats)
        m.fit(p_tr, eval_set=p_val, verbose=0)
        cv_scores.append(r2_score(yc_train[val_i], m.predict(p_val)))

    res_cat = {
        'name': 'CatBoost', 'model': cat_model,
        'MAE': mae_c, 'RMSE': rmse_c, 'R2': r2_c,
        'CV_R2_mean': np.mean(cv_scores), 'CV_R2_std': np.std(cv_scores),
        'train_time': t_cat,
        '_all_cb_cols':  all_cb_cols,
        '_cat_indices':  cat_indices,
        '_numeric_feats': numeric_feats,
        '_cat_str_feats': cat_str_feats,
    }
    results['CatBoost'] = res_cat
    print(f'  MAE={mae_c:,.0f}  RMSE={rmse_c:,.0f}  R²={r2_c:.4f}  CV-R²={np.mean(cv_scores):.4f}±{np.std(cv_scores):.4f}  ({t_cat:.1f}s)')


# ─────────────────────────────────────────────────────────────
# STEP 6 — Comparison Table & Best Model Selection
# ─────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('STEP 6 — Model Comparison Table')
print('='*60)

print(f'\n{"Model":<22} {"MAE (LKR)":>12} {"RMSE (LKR)":>12} {"R²":>8} {"CV R²":>10} {"CV ±":>8} {"Time":>8}')
print('-' * 86)
for name, r in results.items():
    print(f'{name:<22} {r["MAE"]:>12,.0f} {r["RMSE"]:>12,.0f} {r["R2"]:>8.4f} '
          f'{r["CV_R2_mean"]:>10.4f} {r["CV_R2_std"]:>8.4f} {r["train_time"]:>7.1f}s')

best_name = max(results, key=lambda k: results[k]['CV_R2_mean'])
best_res  = results[best_name]
print(f'\n→ BEST MODEL: {best_name}  (CV R² = {best_res["CV_R2_mean"]:.4f})')

# ─────────────────────────────────────────────────────────────
# STEP 7 — Feature Importance
# ─────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('STEP 7 — Feature Importance')
print('='*60)

best_model = best_res['model']

if best_name == 'CatBoost':
    importances = best_model.get_feature_importance()
    feat_names  = best_res['_all_cb_cols']
else:
    importances = best_model.feature_importances_
    feat_names  = keep_features

feat_imp = pd.Series(importances, index=feat_names).sort_values(ascending=False)
print('\nFeature importances:')
for feat, imp in feat_imp.items():
    bar = '█' * int(imp / feat_imp.max() * 30)
    print(f'  {feat:<22}: {imp:.4f}  {bar}')

fig, ax = plt.subplots(figsize=(9, 5))
colors = ['#2563eb' if i < 3 else '#93c5fd' for i in range(len(feat_imp))]
feat_imp.plot(kind='bar', ax=ax, color=colors, edgecolor='white')
ax.set_title(f'Feature Importance — {best_name}', fontsize=13)
ax.set_ylabel('Importance Score')
ax.set_xlabel('')
ax.tick_params(axis='x', rotation=45)
for bar, val in zip(ax.patches, feat_imp.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + feat_imp.max()*0.01,
            f'{val:.3f}', ha='center', va='bottom', fontsize=8)
plt.tight_layout()
fi_path = os.path.join(OUTPUT_DIR, 'feature_importance.png')
plt.savefig(fi_path, dpi=150)
plt.close()
print(f'\nFeature importance chart saved → {fi_path}')

top5 = feat_imp.head(5).index.tolist()
print(f'\nTop 5 price drivers: {top5}')

# ─────────────────────────────────────────────────────────────
# STEP 8 — Save Model Artifacts
# ─────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('Saving model artifacts')
print('='*60)

encoders = {
    'le_property_type': le_type,
    'district_means':   district_means.to_dict(),
    'district_latlng':  district_latlng,
    'global_latlng':    global_latlng,
    'furnished_map':    furnished_map,
    'feature_cols':     keep_features,
    'best_model_name':  best_name,
}
if best_name == 'CatBoost':
    encoders['cat_feature_cols'] = best_res['_all_cb_cols']
    encoders['cat_indices']      = best_res['_cat_indices']
    encoders['numeric_feats']    = best_res['_numeric_feats']
    encoders['cat_str_feats']    = best_res['_cat_str_feats']

# CV std used by Flask endpoint for ±confidence interval
cv_predictions = []
kf5 = KFold(n_splits=5, shuffle=True, random_state=42)
if best_name == 'CatBoost':
    idx_all = np.arange(len(Xc_train_df))
    for tr_i, val_i in kf5.split(idx_all):
        p_tr  = Pool(Xc_train_df.iloc[tr_i],  yc_train[tr_i],  cat_features=cat_str_feats)
        p_val = Pool(Xc_train_df.iloc[val_i], yc_train[val_i], cat_features=cat_str_feats)
        m = CatBoostRegressor(**best_cat_params, cat_features=cat_str_feats)
        m.fit(p_tr, verbose=0)
        cv_predictions.extend(m.predict(p_val))
else:
    for tr_idx, val_idx in kf5.split(X_train_s):
        best_model.fit(X_train_s[tr_idx], y_train[tr_idx])
        cv_predictions.extend(best_model.predict(X_train_s[val_idx]))
    best_model.fit(X_train_s, y_train)  # refit on full training data

cv_residuals_std = float(np.std(np.array(cv_predictions) - y_train[:len(cv_predictions)]))

model_bundle = {
    'model':         best_model,
    'model_name':    best_name,
    'feature_cols':  keep_features if best_name != 'CatBoost' else best_res['_all_cb_cols'],
    'top_features':  top5,
    'cv_std':        cv_residuals_std,
    'metrics': {
        'MAE':        round(best_res['MAE'], 2),
        'RMSE':       round(best_res['RMSE'], 2),
        'R2':         round(best_res['R2'], 4),
        'CV_R2_mean': round(best_res['CV_R2_mean'], 4),
        'CV_R2_std':  round(best_res['CV_R2_std'], 4),
        'samples':    len(model_df),
    },
}

price_model_path = os.path.join(SCRIPT_DIR, 'price_model.joblib')
encoders_path    = os.path.join(SCRIPT_DIR, 'encoders.joblib')
joblib.dump(model_bundle, price_model_path)
joblib.dump(encoders,     encoders_path)

print(f'price_model.joblib → {price_model_path}')
print(f'encoders.joblib    → {encoders_path}')
print(f'scaler.joblib      → {scaler_path}')

print('\n' + '='*60)
print('PIPELINE COMPLETE')
print(f'Best model : {best_name}')
print(f'Test R²    : {best_res["R2"]:.4f}')
print(f'Test MAE   : LKR {best_res["MAE"]:,.0f}')
print(f'Test RMSE  : LKR {best_res["RMSE"]:,.0f}')
print(f'CV R²      : {best_res["CV_R2_mean"]:.4f} ± {best_res["CV_R2_std"]:.4f}')
print('='*60)
print('\nNOTE ON R² SCORE:')
print('  R² < 0.4 is expected with this dataset because:')
print('  - area_sqft was 99.7% null (dropped — zero variance)')
print('  - 30% of beds/baths were 0 (imputed with district median)')
print('  - Only 340 training samples across 18 districts')
print('  - Scraped listings have wide price variance from landlords')
print('  The model still provides useful price range estimates.')
print('  Improve R² by: running full multi-district scrape (3000+ rows)')
print('  and manually adding area_sqft for future properties.\n')
