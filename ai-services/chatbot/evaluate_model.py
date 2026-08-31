"""
Evaluation-only script for the Chatbot intent classifier (:8003).

Does NOT retrain and does NOT touch app.py — it imports the exact same
TRAINING_DATA list and pipeline architecture (TfidfVectorizer(ngram_range=(1,2),
max_features=5000) + MultinomialNB(alpha=0.5)) defined in app.py, WITHOUT
calling app.py's module-level load_or_train_model() (Flask app object is
never instantiated here, so this does not start a server or touch
chatbot_model.joblib).

Why cross-validation instead of a train/test split:
  app.py trains on ALL 49 examples with no held-out set at all (there's no
  test data to evaluate against). With only ~4-6 examples per intent, a
  single 80/20 split would leave ~1 example per class in the test set -- not
  statistically meaningful. Stratified 4-fold CV (the max fold count the
  smallest class, 4 examples, supports) evaluates every example exactly once
  out-of-fold, which is the standard, defensible approach for a dataset this
  small.

Usage: python evaluate_model.py
Outputs written to: outputs/
"""
import os
import importlib.util
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import confusion_matrix, classification_report, f1_score, accuracy_score

HERE = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(HERE, 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

sns.set_style('whitegrid')
plt.rcParams['figure.dpi'] = 150

# ── Pull TRAINING_DATA straight out of app.py without executing/importing it
# (importing app.py would create a Flask app and call load_or_train_model()) ─
app_path = os.path.join(HERE, 'app.py')
with open(app_path, 'r', encoding='utf-8') as f:
    app_src = f.read()
namespace = {}
# Execute only the TRAINING_DATA literal by slicing the source between markers
start = app_src.index('TRAINING_DATA = [')
end = app_src.index(']', app_src.index('"general_faq")')) + 1
exec(app_src[start:end], namespace)
TRAINING_DATA = namespace['TRAINING_DATA']

texts = [t for t, _ in TRAINING_DATA]
intents = [i for _, i in TRAINING_DATA]

print(f'Loaded {len(texts)} training examples across {len(set(intents))} intents')
counts = pd.Series(intents).value_counts()
print('\nExamples per intent:')
print(counts.to_string())

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Dataset composition (context: this is a very small dataset)
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 5))
counts.sort_values().plot(kind='barh', ax=ax, color='#2563eb', edgecolor='white')
ax.set_xlabel('Number of training examples')
ax.set_title(f'Chatbot Training Data Composition — {len(texts)} examples, {len(counts)} intents', fontsize=12)
for i, v in enumerate(counts.sort_values().values):
    ax.text(v + 0.05, i, str(v), va='center', fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_dataset_composition.png'), dpi=150, bbox_inches='tight')
plt.close()
print('\nSaved fig_dataset_composition.png')

# ── Cross-validated evaluation (identical pipeline architecture to app.py) ──
le = LabelEncoder()
y = le.fit_transform(intents)
min_class_count = counts.min()
n_splits = min(4, min_class_count)
print(f'\nUsing StratifiedKFold(n_splits={n_splits}) — smallest intent has {min_class_count} examples')

skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
    ('clf', MultinomialNB(alpha=0.5)),
])

y_pred = cross_val_predict(pipeline, texts, y, cv=skf)
labels_sorted = sorted(set(y))
label_names = le.inverse_transform(labels_sorted)

f1_macro = f1_score(y, y_pred, average='macro')
acc = accuracy_score(y, y_pred)
print(f'\nOut-of-fold accuracy: {acc:.4f}')
print(f'Out-of-fold F1 (macro): {f1_macro:.4f}')

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Confusion Matrix (out-of-fold, every example evaluated once)
# ═══════════════════════════════════════════════════════════════════════════
cm = confusion_matrix(y, y_pred, labels=labels_sorted)
fig, ax = plt.subplots(figsize=(9, 8))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
            xticklabels=label_names, yticklabels=label_names, ax=ax, annot_kws={'size': 11})
ax.set_xlabel('Predicted intent')
ax.set_ylabel('True intent')
ax.set_title(f'Confusion Matrix — Chatbot Intent Classifier\n'
             f'{n_splits}-fold stratified CV (out-of-fold), acc={acc:.3f}, F1(macro)={f1_macro:.3f}',
             fontsize=12)
plt.xticks(rotation=40, ha='right')
plt.yticks(rotation=0)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_confusion_matrix.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig_confusion_matrix.png')

# ═══════════════════════════════════════════════════════════════════════════
# Figure — Per-intent F1 score
# ═══════════════════════════════════════════════════════════════════════════
report_dict = classification_report(y, y_pred, target_names=label_names, output_dict=True, zero_division=0)
per_intent_f1 = pd.Series({k: v['f1-score'] for k, v in report_dict.items()
                            if k not in ('accuracy', 'macro avg', 'weighted avg')}).sort_values()

fig, ax = plt.subplots(figsize=(8, 5))
colors = ['#dc2626' if v < 0.5 else '#f59e0b' if v < 0.75 else '#16a34a' for v in per_intent_f1.values]
per_intent_f1.plot(kind='barh', ax=ax, color=colors, edgecolor='white')
ax.set_xlabel('F1 score')
ax.set_xlim(0, 1.05)
ax.set_title('Per-Intent F1 Score (out-of-fold CV)', fontsize=12)
for i, v in enumerate(per_intent_f1.values):
    ax.text(v + 0.01, i, f'{v:.2f}', va='center', fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'fig_per_intent_f1.png'), dpi=150, bbox_inches='tight')
plt.close()
print('Saved fig_per_intent_f1.png')

# ── Text report ───────────────────────────────────────────────────────────
report_text = classification_report(y, y_pred, target_names=label_names, zero_division=0)
with open(os.path.join(OUTPUT_DIR, 'table_classification_report.txt'), 'w') as f:
    f.write('Chatbot Intent Classifier — Cross-Validated Evaluation\n')
    f.write('=' * 60 + '\n')
    f.write(f'Total examples: {len(texts)}\n')
    f.write(f'Intents: {len(counts)}\n')
    f.write(f'Evaluation method: {n_splits}-fold stratified cross-validation (out-of-fold predictions)\n')
    f.write('Reason: app.py trains on all examples with no held-out set; dataset is\n')
    f.write('too small (4-6 examples/intent) for a single train/test split to be meaningful.\n\n')
    f.write(f'Accuracy: {acc:.4f}\n')
    f.write(f'F1 (macro): {f1_macro:.4f}\n\n')
    f.write(report_text)
    f.write('\n\nExamples per intent:\n')
    f.write(counts.to_string())
print('Saved table_classification_report.txt')

print('\n' + '=' * 60)
print('SUMMARY')
print('=' * 60)
print(f'Examples: {len(texts)}  |  Intents: {len(counts)}  |  CV folds: {n_splits}')
print(f'Accuracy: {acc:.4f}')
print(f'F1 (macro): {f1_macro:.4f}')
print(f'\nAll outputs saved to: {OUTPUT_DIR}')
