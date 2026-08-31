"""
Evaluation-only script for the SafeRent disaster classifier (:8004).

Does NOT retrain and does NOT touch app.py / train_model.py — it loads the
already-trained `location_model.joblib` and reconstructs the exact same
train/test split used inside app.py's /train route (same dataset file, same
feature engineering, same random_state=42 / test_size=0.2 / stratify=y), then
runs the saved model on the held-out test rows to produce evaluation figures
for the report.

Usage: python evaluate_model.py
Outputs written to: outputs/
"""
import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix, classification_report, roc_auc_score, roc_curve,
    precision_recall_curve, average_precision_score, ConfusionMatrixDisplay,
)

HERE = os.path.dirname(__file__)
DATASET_PATH = os.path.join(HERE, 'uploaded_dataset.csv')
MODEL_PATH = os.path.join(HERE, 'location_model.joblib')
OUTPUT_DIR = os.path.join(HERE, 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

sns.set_style('whitegrid')
plt.rcParams['figure.dpi'] = 150

print('Loading trained model bundle...')
bundle = joblib.load(MODEL_PATH)
model = bundle['model']
le = bundle['le']
feature_cols = bundle['features']

print(f'Loading dataset from: {DATASET_PATH}')
df = pd.read_csv(DATASET_PATH, low_memory=False)
print(f'Loaded {len(df):,} rows across {df["district"].nunique()} districts')

# ── Reproduce the EXACT feature engineering from app.py's /train route ──────
df['district_enc'] = le.transform(df['district'].fillna('Unknown'))

season_map = {'NE_monsoon': 0, 'SW_monsoon': 1, 'inter_monsoon_1': 2,
              'inter_monsoon_2': 3, 'dry': 4}
df['season_enc'] = df['season'].map(season_map).fillna(2)

df[feature_cols] = df[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
df['disaster_occurred'] = pd.to_numeric(df['disaster_occurred'], errors='coerce').fillna(0).astype(int)

X = df[feature_cols]
y = df['disaster_occurred']

# Identical split params to app.py -> reproduces the identical held-out test set
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                           random_state=42, stratify=y)
print(f'Test set: {len(X_te):,} rows ({y_te.mean()*100:.2f}% positive)')

# ── Predictions on the held-out test set ─────────────────────────────────────
y_pred = model.predict(X_te)
y_proba = model.predict_proba(X_te)[:, 1]

# ═══════════════════════════════════════════════════════════════════════════
# Figure 7.1 — Confusion Matrix
# ═══════════════════════════════════════════════════════════════════════════
labels = ['No Disaster', 'Disaster']
cm = confusion_matrix(y_te, y_pred)
cm_norm = confusion_matrix(y_te, y_pred, normalize='true')

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
sns.heatmap(cm, annot=True, fmt=',d', cmap='Blues', cbar=False,
            xticklabels=labels, yticklabels=labels, ax=axes[0],
            annot_kws={'size': 13})
axes[0].set_title('Confusion Matrix (counts)', fontsize=12)
axes[0].set_xlabel('Predicted label')
axes[0].set_ylabel('True label')

sns.heatmap(cm_norm, annot=True, fmt='.2%', cmap='Blues', cbar=False,
            xticklabels=labels, yticklabels=labels, ax=axes[1],
            annot_kws={'size': 13})
axes[1].set_title('Confusion Matrix (row-normalised)', fontsize=12)
axes[1].set_xlabel('Predicted label')
axes[1].set_ylabel('True label')

fig.suptitle('Figure 7.1: Confusion Matrix — SafeRent Disaster Classifier (RandomForest)', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig7_1_confusion_matrix.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig7_1_confusion_matrix.png')

# ═══════════════════════════════════════════════════════════════════════════
# Figure 7.2 — ROC Curve
# ═══════════════════════════════════════════════════════════════════════════
fpr, tpr, _ = roc_curve(y_te, y_proba)
auc = roc_auc_score(y_te, y_proba)

fig, ax = plt.subplots(figsize=(6.5, 6))
ax.plot(fpr, tpr, color='#2563eb', lw=2.2, label=f'RandomForest (AUC = {auc:.4f})')
ax.plot([0, 1], [0, 1], color='grey', lw=1, linestyle='--', label='Random classifier')
ax.set_xlabel('False Positive Rate')
ax.set_ylabel('True Positive Rate')
ax.set_title('Figure 7.2: ROC Curve — Disaster Classifier', fontsize=12)
ax.legend(loc='lower right')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig7_2_roc_curve.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig7_2_roc_curve.png')

# ═══════════════════════════════════════════════════════════════════════════
# Figure 7.3 — Precision-Recall Curve (informative given ~10.8% class imbalance)
# ═══════════════════════════════════════════════════════════════════════════
prec, rec, _ = precision_recall_curve(y_te, y_proba)
ap = average_precision_score(y_te, y_proba)
baseline = y_te.mean()

fig, ax = plt.subplots(figsize=(6.5, 6))
ax.plot(rec, prec, color='#16a34a', lw=2.2, label=f'RandomForest (AP = {ap:.4f})')
ax.axhline(baseline, color='grey', lw=1, linestyle='--',
           label=f'No-skill baseline ({baseline:.3f})')
ax.set_xlabel('Recall')
ax.set_ylabel('Precision')
ax.set_title('Figure 7.3: Precision–Recall Curve — Disaster Classifier', fontsize=12)
ax.legend(loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig7_3_precision_recall_curve.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig7_3_precision_recall_curve.png')

# ═══════════════════════════════════════════════════════════════════════════
# Figure 7.4 — Feature Importance
# ═══════════════════════════════════════════════════════════════════════════
importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(8, 6))
importances.plot(kind='barh', ax=ax, color='#2563eb')
ax.set_title('Figure 7.4: Feature Importance — Disaster Classifier (RandomForest)', fontsize=12)
ax.set_xlabel('Gini importance')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig7_4_feature_importance.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig7_4_feature_importance.png')

# ═══════════════════════════════════════════════════════════════════════════
# Figure 7.5 — Predicted probability distribution by true class
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 5))
sns.histplot(x=y_proba[y_te == 0], bins=50, color='#2563eb', alpha=0.6,
             label='True: No Disaster', stat='density', ax=ax)
sns.histplot(x=y_proba[y_te == 1], bins=50, color='#dc2626', alpha=0.6,
             label='True: Disaster', stat='density', ax=ax)
ax.axvline(0.5, color='black', lw=1, linestyle='--', label='Default threshold (0.5)')
ax.set_xlabel('Predicted disaster probability')
ax.set_title('Figure 7.5: Predicted Probability Distribution by True Class', fontsize=12)
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig7_5_probability_distribution.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig7_5_probability_distribution.png')

# ═══════════════════════════════════════════════════════════════════════════
# Table 7.x — Classification report (text + CSV for the report appendix)
# ═══════════════════════════════════════════════════════════════════════════
report_dict = classification_report(y_te, y_pred, target_names=labels, output_dict=True)
report_df = pd.DataFrame(report_dict).transpose()
report_df.to_csv(os.path.join(OUTPUT_DIR, 'table7_classification_report.csv'))

report_text = classification_report(y_te, y_pred, target_names=labels)
with open(os.path.join(OUTPUT_DIR, 'table7_classification_report.txt'), 'w') as f:
    f.write('SafeRent Disaster Classifier — Held-out Test Set Evaluation\n')
    f.write('=' * 65 + '\n')
    f.write(f'Test set size: {len(X_te):,} rows (20% split, stratified)\n')
    f.write(f'Positive class rate (test): {y_te.mean()*100:.2f}%\n')
    f.write(f'AUC-ROC: {auc:.4f}\n')
    f.write(f'Average Precision (PR-AUC): {ap:.4f}\n\n')
    f.write(report_text)
    f.write('\n\nConfusion Matrix (rows=true, cols=predicted):\n')
    f.write(f'                 Pred: No Disaster   Pred: Disaster\n')
    f.write(f'True: No Disaster   {cm[0,0]:>10,}       {cm[0,1]:>10,}\n')
    f.write(f'True: Disaster      {cm[1,0]:>10,}       {cm[1,1]:>10,}\n')

print('Saved table7_classification_report.csv / .txt')

print('\n' + '=' * 60)
print('SUMMARY')
print('=' * 60)
print(f'AUC-ROC:   {auc:.4f}')
print(f'Accuracy:  {report_dict["accuracy"]:.4f}')
print(f'Precision (Disaster): {report_dict["Disaster"]["precision"]:.4f}')
print(f'Recall (Disaster):    {report_dict["Disaster"]["recall"]:.4f}')
print(f'F1 (Disaster):        {report_dict["Disaster"]["f1-score"]:.4f}')
print(f'\nAll outputs saved to: {OUTPUT_DIR}')
