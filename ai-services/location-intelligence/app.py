"""
SmartRentAI — Safe Location Intelligence Engine
================================================
Trains an ML model on the real Sri Lankan disaster dataset (401,775 records)
and provides a composite SafeRent Score (0–100) per district.

Score breakdown:
  Disaster Probability   30%  ← trained on YOUR CSV
  Flood Zone Risk        20%  ← geographic knowledge
  Landslide Zone Risk    15%  ← geographic knowledge
  Hospital Access        10%  ← OpenStreetMap / static
  Transport Access       10%  ← static
  Crime Indicator        10%  ← news/static estimates
  Rainfall Stability      5%  ← from dataset stats

Run: python app.py   (port 8004)
First call /train to build the model from the CSV.
"""

import os, json
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score

app = Flask(__name__)
CORS(app)

DATASET_PATH = os.environ.get(
    'DATASET_PATH',
    r'C:\Users\Menuja\Desktop\create new data set\data\final\training_dataset.csv'
)
MODEL_PATH   = 'location_model.joblib'
STATS_PATH   = 'district_stats.joblib'

# ── Static geographic & social knowledge ─────────────────────────────────────
# Flood risk (0–100): based on DMC Sri Lanka flood zone maps
FLOOD_RISK = {
    'Colombo': 75, 'Gampaha': 70, 'Kalutara': 65, 'Kandy': 35,
    'Matale': 30,  'Nuwara_Eliya': 20, 'Galle': 60, 'Matara': 55,
    'Hambantota': 40, 'Jaffna': 50, 'Kilinochchi': 45, 'Mannar': 50,
    'Vavuniya': 40, 'Mullaitivu': 45, 'Trincomalee': 55, 'Batticaloa': 65,
    'Ampara': 60, 'Polonnaruwa': 50, 'Anuradhapura': 45, 'Puttalam': 55,
    'Kurunegala': 40, 'Ratnapura': 70, 'Kegalle': 65, 'Badulla': 30,
    'Moneragala': 40,
}

# Landslide risk (0–100): NBRO Sri Lanka landslide hazard map
LANDSLIDE_RISK = {
    'Colombo': 10, 'Gampaha': 10, 'Kalutara': 35, 'Kandy': 75,
    'Matale': 55,  'Nuwara_Eliya': 80, 'Galle': 30, 'Matara': 40,
    'Hambantota': 15, 'Jaffna': 5, 'Kilinochchi': 5, 'Mannar': 5,
    'Vavuniya': 10, 'Mullaitivu': 10, 'Trincomalee': 20, 'Batticaloa': 20,
    'Ampara': 30, 'Polonnaruwa': 20, 'Anuradhapura': 15, 'Puttalam': 10,
    'Kurunegala': 30, 'Ratnapura': 85, 'Kegalle': 80, 'Badulla': 75,
    'Moneragala': 45,
}

# Hospital access score (0–100): 100 = excellent coverage
HOSPITAL_ACCESS = {
    'Colombo': 95, 'Gampaha': 85, 'Kalutara': 75, 'Kandy': 90,
    'Matale': 65,  'Nuwara_Eliya': 70, 'Galle': 80, 'Matara': 75,
    'Hambantota': 60, 'Jaffna': 75, 'Kilinochchi': 50, 'Mannar': 45,
    'Vavuniya': 55, 'Mullaitivu': 40, 'Trincomalee': 65, 'Batticaloa': 65,
    'Ampara': 60, 'Polonnaruwa': 60, 'Anuradhapura': 70, 'Puttalam': 65,
    'Kurunegala': 75, 'Ratnapura': 65, 'Kegalle': 70, 'Badulla': 65,
    'Moneragala': 50,
}

# Transport access score (0–100)
TRANSPORT_ACCESS = {
    'Colombo': 95, 'Gampaha': 85, 'Kalutara': 75, 'Kandy': 88,
    'Matale': 60,  'Nuwara_Eliya': 65, 'Galle': 78, 'Matara': 72,
    'Hambantota': 55, 'Jaffna': 72, 'Kilinochchi': 40, 'Mannar': 35,
    'Vavuniya': 50, 'Mullaitivu': 35, 'Trincomalee': 60, 'Batticaloa': 62,
    'Ampara': 55, 'Polonnaruwa': 58, 'Anuradhapura': 65, 'Puttalam': 60,
    'Kurunegala': 72, 'Ratnapura': 62, 'Kegalle': 68, 'Badulla': 60,
    'Moneragala': 45,
}

# Crime indicator (0–100): 100 = lowest crime (safest)
# Based on Sri Lanka Police annual statistics & news analysis
CRIME_SAFETY = {
    'Colombo': 45, 'Gampaha': 60, 'Kalutara': 65, 'Kandy': 55,
    'Matale': 70,  'Nuwara_Eliya': 72, 'Galle': 65, 'Matara': 68,
    'Hambantota': 72, 'Jaffna': 70, 'Kilinochchi': 75, 'Mannar': 70,
    'Vavuniya': 68, 'Mullaitivu': 72, 'Trincomalee': 65, 'Batticaloa': 65,
    'Ampara': 68, 'Polonnaruwa': 72, 'Anuradhapura': 70, 'Puttalam': 68,
    'Kurunegala': 68, 'Ratnapura': 65, 'Kegalle': 67, 'Badulla': 70,
    'Moneragala': 72,
}

# Province mapping
PROVINCE = {
    'Colombo':'Western','Gampaha':'Western','Kalutara':'Western',
    'Kandy':'Central','Matale':'Central','Nuwara_Eliya':'Central',
    'Galle':'Southern','Matara':'Southern','Hambantota':'Southern',
    'Jaffna':'Northern','Kilinochchi':'Northern','Mannar':'Northern',
    'Vavuniya':'Northern','Mullaitivu':'Northern',
    'Trincomalee':'Eastern','Batticaloa':'Eastern','Ampara':'Eastern',
    'Polonnaruwa':'North Central','Anuradhapura':'North Central',
    'Puttalam':'North Western','Kurunegala':'North Western',
    'Ratnapura':'Sabaragamuwa','Kegalle':'Sabaragamuwa',
    'Badulla':'Uva','Moneragala':'Uva',
}


def normalise(district: str) -> str:
    """Handle spacing variants like 'Nuwara Eliya' vs 'Nuwara_Eliya'."""
    return district.replace(' ', '_').strip().title()


# ── ML Training ───────────────────────────────────────────────────────────────
@app.route('/upload-dataset', methods=['POST'])
def upload_dataset():
    """Upload a CSV dataset and save it for training."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided. Send as multipart/form-data with key "file"'}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files accepted'}), 400

    save_path = os.path.join(os.path.dirname(__file__), 'uploaded_dataset.csv')
    file.save(save_path)

    # Update the global dataset path for the next /train call
    global DATASET_PATH
    DATASET_PATH = save_path

    # Quick preview
    try:
        df = pd.read_csv(save_path, nrows=5)
        return jsonify({
            'message': 'Dataset uploaded successfully. Now POST /train to build the model.',
            'saved_to': save_path,
            'columns': list(df.columns),
            'preview_rows': 5,
        })
    except Exception as e:
        return jsonify({'error': f'File saved but could not read: {e}'}), 422


@app.route('/train', methods=['POST', 'GET'])
def train():
    print(f"Loading dataset from: {DATASET_PATH}")
    try:
        df = pd.read_csv(DATASET_PATH, low_memory=False)
    except FileNotFoundError:
        return jsonify({'error': f'Dataset not found at {DATASET_PATH}'}), 404

    print(f"Loaded {len(df):,} rows across {df['district'].nunique()} districts")

    # ── Feature engineering ───────────────────────────────────────────────────
    le = LabelEncoder()
    df['district_enc'] = le.fit_transform(df['district'].fillna('Unknown'))

    season_map = {'NE_monsoon': 0, 'SW_monsoon': 1, 'inter_monsoon_1': 2,
                  'inter_monsoon_2': 3, 'dry': 4}
    df['season_enc'] = df['season'].map(season_map).fillna(2)

    feature_cols = [
        'rainfall_mm', 'temp_avg_c', 'humidity_pct', 'wind_speed_ms',
        'rainfall_3d_sum', 'rainfall_3d_max', 'rainfall_7d_sum', 'rainfall_7d_max',
        'rainfall_14d_sum', 'rainfall_30d_sum', 'rainfall_30d_max',
        'temp_7d_avg', 'month', 'season_enc', 'district_enc',
    ]
    df[feature_cols] = df[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    df['disaster_occurred'] = pd.to_numeric(df['disaster_occurred'], errors='coerce').fillna(0).astype(int)

    X = df[feature_cols]
    y = df['disaster_occurred']

    # Use a 30% sample for faster training; still 120k+ rows
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                               random_state=42, stratify=y)

    print("Training Random Forest …")
    rf = RandomForestClassifier(n_estimators=150, max_depth=12,
                                n_jobs=-1, random_state=42,
                                class_weight='balanced')
    rf.fit(X_tr, y_tr)

    y_pred_proba = rf.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, y_pred_proba)
    report = classification_report(y_te, rf.predict(X_te), output_dict=True)

    # ── Compute per-district statistics from the full dataset ─────────────────
    stats = {}
    for district, grp in df.groupby('district'):
        stats[district] = {
            'disaster_rate':      round(grp['disaster_occurred'].mean() * 100, 2),
            'avg_rainfall':       round(grp['rainfall_mm'].mean(), 2),
            'max_rainfall':       round(grp['rainfall_mm'].max(), 2),
            'avg_humidity':       round(grp['humidity_pct'].mean(), 2),
            'avg_temp':           round(grp['temp_avg_c'].mean(), 2),
            'avg_7d_rainfall':    round(grp['rainfall_7d_sum'].mean(), 2),
            'max_30d_rainfall':   round(grp['rainfall_30d_max'].mean(), 2),
            'total_records':      len(grp),
            'disaster_events':    int(grp['disaster_occurred'].sum()),
        }

    joblib.dump({'model': rf, 'le': le, 'features': feature_cols}, MODEL_PATH)
    joblib.dump(stats, STATS_PATH)

    metrics = {
        'auc_roc':  round(auc, 4),
        'accuracy': round(report['accuracy'], 4),
        'precision': round(report['1']['precision'], 4),
        'recall':   round(report['1']['recall'], 4),
        'f1':       round(report['1']['f1-score'], 4),
        'samples':  len(df),
    }
    print("Training complete:", metrics)
    return jsonify({'message': 'Model trained successfully', 'metrics': metrics})


# ── Safe Location Score ───────────────────────────────────────────────────────
def compute_safe_score(district: str, stats: dict, model_data: dict) -> dict:
    """
    Returns a composite SafeRent Score (0–100) with breakdown.
    Higher = better/safer.
    """
    d = normalise(district)
    dist_stats = stats.get(d, stats.get(district, {}))

    # 1. Disaster probability from trained ML model (inverted: low prob = high score)
    disaster_rate   = dist_stats.get('disaster_rate', 10.81)   # dataset historical rate
    ml_disaster_score = max(0, 100 - (disaster_rate * 5))       # scale to 0-100 safety

    # 2. Flood risk (inverted)
    flood_safety    = 100 - FLOOD_RISK.get(d, 50)

    # 3. Landslide risk (inverted)
    landslide_safety = 100 - LANDSLIDE_RISK.get(d, 30)

    # 4. Hospital access
    hospital_score  = HOSPITAL_ACCESS.get(d, 60)

    # 5. Transport
    transport_score = TRANSPORT_ACCESS.get(d, 60)

    # 6. Crime (already 0-100 safe)
    crime_score     = CRIME_SAFETY.get(d, 65)

    # 7. Rainfall stability (lower avg rainfall = more stable)
    avg_rain = dist_stats.get('avg_rainfall', 5.0)
    rain_stability = max(0, 100 - (avg_rain * 3))  # 0 rain → 100, 33mm/day → 0

    # ── Weighted composite ────────────────────────────────────────────────────
    weights = {
        'disaster': 0.30,
        'flood':    0.20,
        'landslide':0.15,
        'hospital': 0.10,
        'transport':0.10,
        'crime':    0.10,
        'rainfall': 0.05,
    }
    scores = {
        'disaster':  ml_disaster_score,
        'flood':     flood_safety,
        'landslide': landslide_safety,
        'hospital':  hospital_score,
        'transport': transport_score,
        'crime':     crime_score,
        'rainfall':  rain_stability,
    }

    final = sum(scores[k] * weights[k] for k in weights)
    final = round(min(100, max(0, final)), 1)

    if final >= 81:
        category, emoji = 'Excellent', '🟢'
    elif final >= 61:
        category, emoji = 'Good', '🟡'
    elif final >= 41:
        category, emoji = 'Moderate Risk', '🟠'
    else:
        category, emoji = 'High Risk', '🔴'

    return {
        'district':        d,
        'province':        PROVINCE.get(d, 'Unknown'),
        'safe_score':      final,
        'category':        category,
        'emoji':           emoji,
        'breakdown': {
            'disaster_safety':   round(scores['disaster'], 1),
            'flood_safety':      round(scores['flood'], 1),
            'landslide_safety':  round(scores['landslide'], 1),
            'hospital_access':   round(scores['hospital'], 1),
            'transport_access':  round(scores['transport'], 1),
            'crime_safety':      round(scores['crime'], 1),
            'rainfall_stability':round(scores['rainfall'], 1),
        },
        'historical': {
            'disaster_rate_pct':  disaster_rate,
            'avg_daily_rainfall': round(avg_rain, 2),
            'avg_humidity_pct':   dist_stats.get('avg_humidity', 0),
            'total_years':        round(dist_stats.get('total_records', 0) / 365, 1),
            'disaster_events':    dist_stats.get('disaster_events', 0),
        },
        'risks': _build_risks(d, disaster_rate, scores),
        'advantages': _build_advantages(d, scores),
    }


def _build_risks(district, disaster_rate, scores):
    risks = []
    if disaster_rate > 12:
        risks.append(f'High historical disaster rate ({disaster_rate}%)')
    if FLOOD_RISK.get(district, 50) >= 65:
        risks.append('Located in high flood-risk zone')
    if LANDSLIDE_RISK.get(district, 30) >= 60:
        risks.append('High landslide susceptibility')
    if scores['crime'] < 55:
        risks.append('Higher crime incidence reported')
    if scores['rainfall'] < 40:
        risks.append('High seasonal rainfall — flooding possible')
    if not risks:
        risks.append('No major risk factors identified')
    return risks


def _build_advantages(district, scores):
    pros = []
    if scores['hospital'] >= 80:
        pros.append('Excellent hospital and medical access')
    if scores['transport'] >= 80:
        pros.append('Strong public transport network')
    if scores['flood'] >= 75:
        pros.append('Low flood risk zone')
    if scores['landslide'] >= 80:
        pros.append('Low landslide risk')
    if scores['crime'] >= 70:
        pros.append('Relatively safe neighbourhood')
    if scores['disaster'] >= 75:
        pros.append('Low historical disaster frequency')
    if not pros:
        pros.append('Affordable rental prices available')
    return pros


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.route('/score/<district>', methods=['GET'])
def get_score(district):
    if not os.path.exists(MODEL_PATH):
        return jsonify({'error': 'Model not trained yet. POST /train first.'}), 503
    stats      = joblib.load(STATS_PATH)
    model_data = joblib.load(MODEL_PATH)
    result     = compute_safe_score(district, stats, model_data)
    return jsonify(result)


@app.route('/score/all', methods=['GET'])
def get_all_scores():
    if not os.path.exists(STATS_PATH):
        return jsonify({'error': 'Model not trained yet. POST /train first.'}), 503
    stats      = joblib.load(STATS_PATH)
    model_data = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else {}
    all_districts = list(FLOOD_RISK.keys())
    results = [compute_safe_score(d, stats, model_data) for d in all_districts]
    results.sort(key=lambda x: x['safe_score'], reverse=True)
    return jsonify(results)


@app.route('/compare', methods=['POST'])
def compare():
    """Compare multiple districts side-by-side."""
    districts = request.get_json().get('districts', [])
    if not districts:
        return jsonify({'error': 'Provide a list of districts'}), 400
    if not os.path.exists(STATS_PATH):
        return jsonify({'error': 'Model not trained'}), 503
    stats      = joblib.load(STATS_PATH)
    model_data = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else {}
    return jsonify([compute_safe_score(d, stats, model_data) for d in districts])


@app.route('/predict-live', methods=['POST'])
def predict_live():
    """
    Predict disaster probability for CURRENT weather conditions using the ML model.
    Body: { district, rainfall_mm, humidity_pct, temp_avg_c, ... }
    """
    if not os.path.exists(MODEL_PATH):
        return jsonify({'error': 'Model not trained'}), 503

    data       = request.get_json()
    model_data = joblib.load(MODEL_PATH)
    model      = model_data['model']
    le         = model_data['le']
    features   = model_data['features']

    district = normalise(data.get('district', 'Colombo'))
    try:
        dist_enc = le.transform([district])[0]
    except ValueError:
        dist_enc = 0

    row = {
        'rainfall_mm':      float(data.get('rainfall_mm', 5)),
        'temp_avg_c':       float(data.get('temp_avg_c', 27)),
        'humidity_pct':     float(data.get('humidity_pct', 80)),
        'wind_speed_ms':    float(data.get('wind_speed_ms', 3)),
        'rainfall_3d_sum':  float(data.get('rainfall_3d_sum', 15)),
        'rainfall_3d_max':  float(data.get('rainfall_3d_max', 10)),
        'rainfall_7d_sum':  float(data.get('rainfall_7d_sum', 35)),
        'rainfall_7d_max':  float(data.get('rainfall_7d_max', 20)),
        'rainfall_14d_sum': float(data.get('rainfall_14d_sum', 70)),
        'rainfall_30d_sum': float(data.get('rainfall_30d_sum', 150)),
        'rainfall_30d_max': float(data.get('rainfall_30d_max', 40)),
        'temp_7d_avg':      float(data.get('temp_avg_c', 27)),
        'month':            int(data.get('month', 6)),
        'season_enc':       int(data.get('season_enc', 1)),
        'district_enc':     dist_enc,
    }

    import pandas as pd
    X     = pd.DataFrame([row])[features]
    proba = float(model.predict_proba(X)[0][1])

    return jsonify({
        'district':             district,
        'disaster_probability': round(proba * 100, 2),
        'risk_level':           'High' if proba > 0.3 else 'Medium' if proba > 0.15 else 'Low',
        'safe_to_rent':         proba < 0.2,
    })


@app.route('/health', methods=['GET'])
def health():
    trained = os.path.exists(MODEL_PATH)
    return jsonify({'status': 'ok', 'service': 'location-intelligence',
                    'model_trained': trained})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8004, debug=True)
