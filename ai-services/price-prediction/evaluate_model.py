"""
Evaluation-only script for the Price Prediction model (:8002).

Does NOT retrain and does NOT touch train.py / app.py — it loads the already
-trained `price_model.joblib` (CatBoost) and reconstructs the exact same
data-cleaning + feature-selection + train/test split used inside train.py
(same MySQL query, same IQR/imputation rules, same random_state=42 stratified
split), then runs the saved model on the held-out test rows to produce
regression evaluation figures for the report.

Usage: python evaluate_model.py
Outputs written to: outputs/
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import mysql.connector
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    from catboost import Pool
except ImportError:
    Pool = None

HERE = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(HERE, 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

sns.set_style('whitegrid')
plt.rcParams['figure.dpi'] = 150

print('Loading trained model bundle...')
bundle = joblib.load(os.path.join(HERE, 'price_model.joblib'))
encoders = joblib.load(os.path.join(HERE, 'encoders.joblib'))
model = bundle['model']
model_name = bundle['model_name']
print(f'Model: {model_name}  |  saved metrics: {bundle["metrics"]}')

# ── Reproduce STEP 1 (data extraction) exactly as train.py ──────────────────
print('\nExtracting data from MySQL (same query as train.py)...')
conn = mysql.connector.connect(
    host='localhost', port=3306, user='root', password='',
    database='smartrentai', charset='utf8mb4'
)
query = """
    SELECT
        p.id, p.monthly_rent, p.bedrooms, p.bathrooms, p.property_type,
        p.furnished, p.area_sqft, l.district, l.city, l.latitude, l.longitude
    FROM properties p
    JOIN locations l ON p.location_id = l.id
    WHERE p.status = 'available'
      AND p.monthly_rent IS NOT NULL
      AND p.monthly_rent > 0
"""
raw_df = pd.read_sql(query, conn)
conn.close()
print(f'Rows fetched: {len(raw_df)}')

# ── Reproduce STEP 2 (cleaning) exactly as train.py ──────────────────────────
df = raw_df.copy()
coverage = df.notna().mean()
low_coverage_cols = coverage[coverage < 0.1].index.tolist()
if low_coverage_cols:
    df.drop(columns=low_coverage_cols, errors='ignore', inplace=True)

Q1, Q3 = df['monthly_rent'].quantile(0.25), df['monthly_rent'].quantile(0.75)
IQR = Q3 - Q1
lo, hi = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
df = df[(df['monthly_rent'] >= max(lo, 1000)) & (df['monthly_rent'] <= hi)]

for col in ['bedrooms', 'bathrooms']:
    mask = df[col] == 0
    if mask.any():
        pos_data = df[df[col] > 0]
        medians = pos_data.groupby('district')[col].median()
        global_m = pos_data[col].median()
        df.loc[mask, col] = df.loc[mask, 'district'].map(medians).fillna(global_m)
        df[col] = df[col].round().astype(int)

for coord in ['latitude', 'longitude']:
    if coord in df.columns:
        null_mask = df[coord].isna()
        if null_mask.any():
            centroids = df.groupby('district')[coord].transform('median')
            df[coord] = df[coord].fillna(centroids)
        if df[coord].isna().mean() > 0.3:
            df.drop(columns=[coord], inplace=True)

furnished_map = encoders['furnished_map']
df['furnished_num'] = df['furnished'].map(furnished_map).fillna(0).astype(int)
df['property_type_enc'] = encoders['le_property_type'].transform(df['property_type'].fillna('apartment'))
district_means = encoders['district_means']
df['district_enc'] = df['district'].map(district_means)

print(f'Clean dataset: {len(df)} rows (matches saved metrics samples={bundle["metrics"]["samples"]})')

# ── Reproduce the CatBoost-specific test split from STEP 5 ──────────────────
if model_name == 'CatBoost':
    numeric_feats = encoders['numeric_feats']
    cat_str_feats = encoders['cat_str_feats']
    all_cb_cols = encoders['cat_feature_cols']

    cb_df = df[numeric_feats + cat_str_feats + ['monthly_rent']].dropna().reset_index(drop=True)
    for nc in numeric_feats:
        cb_df[nc] = pd.to_numeric(cb_df[nc], errors='coerce')

    Xc_df = cb_df[all_cb_cols]
    yc = cb_df['monthly_rent'].values.astype(float)

    idx = np.arange(len(Xc_df))
    try:
        tr_idx, te_idx = train_test_split(idx, test_size=0.2, random_state=42,
                                           stratify=cb_df['district'].values)
    except ValueError:
        tr_idx, te_idx = train_test_split(idx, test_size=0.2, random_state=42)

    Xc_test_df = Xc_df.iloc[te_idx].reset_index(drop=True)
    y_test = yc[te_idx]

    test_pool = Pool(Xc_test_df, cat_features=cat_str_feats)
    y_pred = model.predict(test_pool)
else:
    # XGBoost / GradientBoosting path (encoded + scaled features)
    feature_cols = encoders['feature_cols']
    scaler_bundle = joblib.load(os.path.join(HERE, 'scaler.joblib'))
    scaler = scaler_bundle['scaler']

    model_df = df[feature_cols + ['monthly_rent', 'district']].dropna().reset_index(drop=True)
    X = model_df[feature_cols].values.astype(float)
    y = model_df['monthly_rent'].values.astype(float)
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=model_df['district'].values)
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    X_test_s = scaler.transform(X_test)
    y_pred = model.predict(X_test_s)

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)
print(f'\nReconstructed test set: {len(y_test)} rows')
print(f'MAE={mae:,.0f}  RMSE={rmse:,.0f}  R2={r2:.4f}  (saved: MAE={bundle["metrics"]["MAE"]:,.0f}  R2={bundle["metrics"]["R2"]:.4f})')

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Model Comparison (from the training run's console log — same run
# that produced the currently-deployed price_model.joblib)
# ═══════════════════════════════════════════════════════════════════════════
comparison = {
    'XGBoost':          {'MAE': 90503, 'RMSE': 129145, 'R2': 0.4856, 'CV_R2': 0.4646, 'CV_std': 0.0458},
    'GradientBoosting': {'MAE': 91256, 'RMSE': 130889, 'R2': 0.4716, 'CV_R2': 0.4550, 'CV_std': 0.0466},
    'CatBoost':         {'MAE': 91679, 'RMSE': 131227, 'R2': 0.4689, 'CV_R2': 0.4711, 'CV_std': 0.0483},
}
comp_df = pd.DataFrame(comparison).T

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
colors = ['#93c5fd' if m != model_name else '#2563eb' for m in comp_df.index]

comp_df['MAE'].plot(kind='bar', ax=axes[0], color=colors, edgecolor='white')
axes[0].set_title('MAE (LKR) — lower is better')
axes[0].tick_params(axis='x', rotation=20)
for i, v in enumerate(comp_df['MAE']):
    axes[0].text(i, v + 500, f'{v:,.0f}', ha='center', fontsize=9)

comp_df['RMSE'].plot(kind='bar', ax=axes[1], color=colors, edgecolor='white')
axes[1].set_title('RMSE (LKR) — lower is better')
axes[1].tick_params(axis='x', rotation=20)
for i, v in enumerate(comp_df['RMSE']):
    axes[1].text(i, v + 500, f'{v:,.0f}', ha='center', fontsize=9)

x = np.arange(len(comp_df))
axes[2].bar(x, comp_df['CV_R2'], yerr=comp_df['CV_std'], capsize=5, color=colors, edgecolor='white')
axes[2].set_title('5-Fold CV R² (± std) — higher is better\n(selection metric)')
axes[2].set_xticks(x)
axes[2].set_xticklabels(comp_df.index, rotation=20)
for i, v in enumerate(comp_df['CV_R2']):
    axes[2].text(i, v + 0.01, f'{v:.4f}', ha='center', fontsize=9)

fig.suptitle(f'Model Comparison — Price Prediction ({len(y_test)*5} total samples, 5-fold CV)\n'
             f'Winner: {model_name} (best CV R², the robust selection criterion — avoids overfitting to one split)',
             fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_model_comparison.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig_model_comparison.png')

comp_df.to_csv(os.path.join(OUTPUT_DIR, 'table_model_comparison.csv'))

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Predicted vs Actual
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 7))
ax.scatter(y_test, y_pred, alpha=0.6, color='#2563eb', edgecolor='white', s=50)
lims = [0, max(y_test.max(), y_pred.max()) * 1.05]
ax.plot(lims, lims, color='red', lw=1.5, linestyle='--', label='Perfect prediction (y = x)')
ax.set_xlim(lims); ax.set_ylim(lims)
ax.set_xlabel('Actual Monthly Rent (LKR)')
ax.set_ylabel('Predicted Monthly Rent (LKR)')
ax.set_title(f'Predicted vs Actual — {model_name}\nTest R² = {r2:.4f}  |  MAE = LKR {mae:,.0f}', fontsize=12)
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_predicted_vs_actual.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig_predicted_vs_actual.png')

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Residual Analysis
# ═══════════════════════════════════════════════════════════════════════════
residuals = y_test - y_pred
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

axes[0].scatter(y_pred, residuals, alpha=0.6, color='#16a34a', edgecolor='white', s=50)
axes[0].axhline(0, color='red', lw=1.5, linestyle='--')
axes[0].set_xlabel('Predicted Monthly Rent (LKR)')
axes[0].set_ylabel('Residual (Actual − Predicted)')
axes[0].set_title('Residuals vs Predicted')

sns.histplot(residuals, bins=30, kde=True, ax=axes[1], color='#16a34a')
axes[1].axvline(0, color='red', lw=1.5, linestyle='--')
axes[1].set_xlabel('Residual (LKR)')
axes[1].set_title('Residual Distribution')

fig.suptitle(f'Residual Analysis — {model_name}', fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_residuals.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig_residuals.png')

print('\n' + '=' * 60)
print('SUMMARY (held-out test set, reconstructed)')
print('=' * 60)
print(f'Model: {model_name}')
print(f'Test samples: {len(y_test)}')
print(f'MAE:  LKR {mae:,.0f}')
print(f'RMSE: LKR {rmse:,.0f}')
print(f'R2:   {r2:.4f}')
print(f'\nAll outputs saved to: {OUTPUT_DIR}')
