"""
Evaluation-only script for the Recommendation model (:8001, Stage 1).

Does NOT retrain and does NOT touch train_profile_model.py / app.py — it loads
the already-trained `profile_model.joblib` (preprocessor + RF classifiers +
RF regressors) and reconstructs the exact same train/test split used inside
train_profile_model.py's train_stage1() (same CSV, same random_state=42,
test_size=0.2), then runs the saved models on the held-out test rows to
produce evaluation figures for the report.

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
from sklearn.model_selection import train_test_split
from sklearn.metrics import (f1_score, accuracy_score, mean_absolute_error,
                              confusion_matrix, classification_report)

HERE = os.path.dirname(__file__)
DS_PATH = os.path.join(HERE, 'data', 'profile_property_dataset.csv')
OUTPUT_DIR = os.path.join(HERE, 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

sns.set_style('whitegrid')
plt.rcParams['figure.dpi'] = 150

DISTRICT_TIER = {
    'Colombo': 1, 'Gampaha': 1,
    'Kandy': 2, 'Kalutara': 2, 'Galle': 2, 'Kurunegala': 2, 'Matara': 2,
    'Jaffna': 2, 'Anuradhapura': 2, 'Ratnapura': 2, 'Batticaloa': 2,
    'Kegalle': 2, 'Trincomalee': 2, 'Puttalam': 2,
    'Matale': 3, 'Nuwara Eliya': 3, 'Hambantota': 3, 'Kilinochchi': 3,
    'Mannar': 3, 'Mullaitivu': 3, 'Vavuniya': 3, 'Ampara': 3,
    'Polonnaruwa': 3, 'Badulla': 3, 'Monaragala': 3,
}
CAT_INPUTS = ['profession', 'age_group', 'family_size', 'preferred_type']
NUM_INPUTS = ['budget', 'has_children', 'has_vehicle', 'current_tier',
              'priority_safety', 'priority_price', 'priority_transport',
              'priority_hospital', 'priority_space']
CLS_TARGETS = ['matched_property_type', 'matched_district_tier']
REG_TARGETS = ['min_saferent_score', 'max_price', 'min_bedrooms',
               'transport_score_min', 'hospital_score_min']

print('Loading trained model bundle...')
bundle = joblib.load(os.path.join(HERE, 'profile_model.joblib'))
pre = bundle['preprocessor']
classifiers = bundle['classifiers']
regressors = bundle['regressors']

print(f'Loading dataset: {DS_PATH}')
df = pd.read_csv(DS_PATH)
df['current_tier'] = df['current_district'].map(DISTRICT_TIER).fillna(2).astype(int)

X = df[CAT_INPUTS + NUM_INPUTS]
Xenc = pre.transform(X)   # use the SAVED, already-fit preprocessor (no refitting)

y_cls = df[CLS_TARGETS]
y_reg = df[REG_TARGETS]

# Identical split params to train_profile_model.py -> reproduces the identical
# held-out test rows (same row order in df -> same indices selected)
Xtr, Xte, ytr_c, yte_c, ytr_r, yte_r = train_test_split(
    Xenc, y_cls, y_reg, test_size=0.2, random_state=42)
print(f'Test set: {Xte.shape[0]:,} rows (reconstructed)')

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Confusion matrices for the 2 classification targets
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
report_lines = ['Recommendation Stage-1 — Held-out Test Set Evaluation',
                 '=' * 60, f'Test set size: {Xte.shape[0]:,} rows\n']

for ax, target in zip(axes, CLS_TARGETS):
    clf = classifiers[target]
    y_pred = clf.predict(Xte)
    y_true = yte_c[target]
    labels = sorted(y_true.unique().tolist())
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
                xticklabels=labels, yticklabels=labels, ax=ax, annot_kws={'size': 11})
    ax.set_xlabel('Predicted')
    ax.set_ylabel('True')
    f1 = f1_score(y_true, y_pred, average='macro')
    acc = accuracy_score(y_true, y_pred)
    ax.set_title(f'{target}\nF1(macro)={f1:.3f}  acc={acc:.3f}', fontsize=11)
    ax.tick_params(axis='x', rotation=30)

    report_lines.append(f'\n--- {target} ---')
    report_lines.append(f'F1 (macro): {f1:.4f}   Accuracy: {acc:.4f}')
    report_lines.append(classification_report(y_true, y_pred))

fig.suptitle('Figure — Confusion Matrices: Stage-1 Classifiers (Profile → Criteria)', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_confusion_matrices.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig_confusion_matrices.png')

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Regression targets: MAE as % of range (bar chart)
# ═══════════════════════════════════════════════════════════════════════════
mae_pct = {}
mae_abs = {}
for t in REG_TARGETS:
    reg = regressors[t]
    pred = reg.predict(Xte)
    mae = mean_absolute_error(yte_r[t], pred)
    rng = yte_r[t].max() - yte_r[t].min()
    mae_abs[t] = mae
    mae_pct[t] = mae / rng * 100
    report_lines.append(f'\n--- {t} (regression) ---')
    report_lines.append(f'MAE: {mae:.2f}   range: {rng:,.0f}   MAE as %% of range: {mae/rng*100:.1f}%%')

fig, ax = plt.subplots(figsize=(9, 5))
series = pd.Series(mae_pct).sort_values()
colors = ['#2563eb' if v < 15 else '#f59e0b' if v < 25 else '#dc2626' for v in series.values]
series.plot(kind='barh', ax=ax, color=colors, edgecolor='white')
ax.set_xlabel('MAE as % of target range (lower is better)')
ax.set_title('Figure — Stage-1 Regressors: Prediction Error by Target', fontsize=12)
for i, v in enumerate(series.values):
    ax.text(v + 0.3, i, f'{v:.1f}%', va='center', fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_regression_mae.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig_regression_mae.png')

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Predicted vs Actual for the 2 highest-stakes regression targets
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
for ax, t in zip(axes, ['max_price', 'min_saferent_score']):
    reg = regressors[t]
    pred = reg.predict(Xte)
    true = yte_r[t].values
    ax.scatter(true, pred, alpha=0.5, color='#2563eb', edgecolor='white', s=40)
    lims = [min(true.min(), pred.min()), max(true.max(), pred.max())]
    ax.plot(lims, lims, color='red', lw=1.5, linestyle='--', label='Perfect prediction')
    ax.set_xlabel(f'Actual {t}')
    ax.set_ylabel(f'Predicted {t}')
    ax.set_title(f'{t}\nMAE={mae_abs[t]:,.1f}', fontsize=11)
    ax.legend(fontsize=8)
fig.suptitle('Figure — Predicted vs Actual: Key Stage-1 Regression Targets', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_regression_scatter.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig_regression_scatter.png')

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Feature importance driving key criteria (proves priorities matter)
# ═══════════════════════════════════════════════════════════════════════════
feat_names = (list(pre.named_transformers_['cat'].get_feature_names_out(CAT_INPUTS))
              + NUM_INPUTS)
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
for ax, t in zip(axes.flat, ['min_saferent_score', 'hospital_score_min', 'transport_score_min', 'max_price']):
    imp = pd.Series(regressors[t].feature_importances_, index=feat_names).sort_values(ascending=False).head(8)
    imp.sort_values().plot(kind='barh', ax=ax, color='#2563eb', edgecolor='white')
    ax.set_title(t, fontsize=11)
    ax.set_xlabel('Importance')
fig.suptitle('Figure — Feature Importance: What Drives Each Predicted Criterion', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_feature_importance.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig_feature_importance.png')

# ═══════════════════════════════════════════════════════════════════════════
# Table — full text report
# ═══════════════════════════════════════════════════════════════════════════
with open(os.path.join(OUTPUT_DIR, 'table_evaluation_report.txt'), 'w') as f:
    f.write('\n'.join(report_lines))
print('Saved table_evaluation_report.txt')

print('\n' + '=' * 60)
print('SUMMARY (held-out test set, reconstructed)')
print('=' * 60)
for t in CLS_TARGETS:
    clf = classifiers[t]
    f1 = f1_score(yte_c[t], clf.predict(Xte), average='macro')
    print(f'{t:24s}  F1(macro)={f1:.4f}')
for t in REG_TARGETS:
    print(f'{t:24s}  MAE={mae_abs[t]:9.2f}  ({mae_pct[t]:.1f}% of range)')
print(f'\nAll outputs saved to: {OUTPUT_DIR}')
