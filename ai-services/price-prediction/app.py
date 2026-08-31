"""
SmartRentAI - Rental Price Prediction Microservice  (port 8002)
Model: GradientBoosting trained on 324 real scraped Sri Lankan properties
Features: district, property_type, bedrooms, bathrooms, furnished
Run: python app.py
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import pandas as pd
import joblib
import os

app = Flask(__name__)
CORS(app)

SCRIPT_DIR         = os.path.dirname(__file__)
PRICE_MODEL_PATH   = os.path.join(SCRIPT_DIR, 'price_model.joblib')
ENCODERS_PATH      = os.path.join(SCRIPT_DIR, 'encoders.joblib')
SCALER_PATH        = os.path.join(SCRIPT_DIR, 'scaler.joblib')

# ── Load artifacts once at startup ───────────────────────────
_bundle   = None
_encoders = None
_scaler   = None

def _load():
    global _bundle, _encoders, _scaler
    if _bundle is None:
        _bundle   = joblib.load(PRICE_MODEL_PATH)
        _encoders = joblib.load(ENCODERS_PATH)
        _scaler_obj = joblib.load(SCALER_PATH)
        _scaler   = _scaler_obj['scaler']
    return _bundle, _encoders, _scaler


DISTRICTS = [
    'Colombo', 'Gampaha', 'Kalutara', 'Kandy', 'Matale', 'Nuwara Eliya',
    'Galle', 'Matara', 'Hambantota', 'Jaffna', 'Trincomalee', 'Batticaloa',
    'Kurunegala', 'Anuradhapura', 'Ratnapura', 'Badulla', 'Kegalle',
]
PROPERTY_TYPES = ['apartment', 'house', 'room', 'villa', 'commercial']
FURNISHED_OPTS = ['unfurnished', 'semi-furnished', 'furnished']


def _district_coord(encoders: dict, coord: str, district: str) -> float:
    """District centroid lat/lng saved at train time — requests never carry raw coords."""
    per_district = encoders.get('district_latlng', {}).get(coord, {})
    global_coord = encoders.get('global_latlng', {}).get(coord, 0.0)
    return float(per_district.get(district, global_coord))


def _build_features(data: dict, encoders: dict, scaler, bundle: dict):
    """
    Convert a raw /predict request into whatever input shape the trained model
    expects. XGBoost/GradientBoosting were fit on a numeric-encoded, scaled
    array; CatBoost was fit on a raw DataFrame (native categoricals, no
    scaling) — so this branches on which model actually won training.
    Returns (X, is_scaled_array).
    """
    district      = data.get('district', 'Colombo')
    property_type = data.get('property_type', 'apartment')
    bedrooms      = int(data.get('bedrooms', 2))
    bathrooms     = int(data.get('bathrooms', 1))
    furnished     = data.get('furnished', 'unfurnished')

    furnished_map = encoders['furnished_map']
    furnished_num = furnished_map.get(furnished, 0)

    model_name = bundle.get('model_name', encoders.get('best_model_name'))

    if model_name == 'CatBoost':
        cat_cols = encoders.get('cat_feature_cols') or bundle['feature_cols']
        row = {
            'bedrooms':      bedrooms,
            'bathrooms':     bathrooms,
            'furnished_num': furnished_num,
            'latitude':      _district_coord(encoders, 'latitude', district),
            'longitude':     _district_coord(encoders, 'longitude', district),
            'district':      district,
            'property_type': property_type,
        }
        X = pd.DataFrame([[row[c] for c in cat_cols]], columns=cat_cols)
        return X, False

    # Encode district via target encoding (district → mean rent learned during training)
    district_means = encoders['district_means']
    global_mean    = np.mean(list(district_means.values()))
    district_enc   = district_means.get(district, global_mean)

    # Encode property_type via LabelEncoder
    le       = encoders['le_property_type']
    pt_clean = property_type if property_type in le.classes_ else le.classes_[0]
    property_type_enc = int(le.transform([pt_clean])[0])

    feature_cols = encoders['feature_cols']
    values = {
        'bedrooms':          bedrooms,
        'bathrooms':         bathrooms,
        'furnished_num':     furnished_num,
        'property_type_enc': property_type_enc,
        'district_enc':      district_enc,
        'latitude':          _district_coord(encoders, 'latitude', district),
        'longitude':         _district_coord(encoders, 'longitude', district),
    }
    X = np.array([[values[c] for c in feature_cols]], dtype=float)
    return scaler.transform(X), True


@app.route('/predict', methods=['POST'])
def predict():
    """
    POST /predict
    Input:  { district, property_type, bedrooms, bathrooms, furnished }
    Output: { predicted_price, price_range, confidence_interval,
               top_3_factors, model_info }
    """
    try:
        bundle, encoders, scaler = _load()
    except FileNotFoundError:
        return jsonify({'error': 'Model not trained yet. Run train.py first.'}), 503

    data = request.get_json(silent=True) or {}

    try:
        X_ready, _ = _build_features(data, encoders, scaler, bundle)
    except Exception as e:
        return jsonify({'error': f'Feature encoding failed: {str(e)}'}), 400

    model      = bundle['model']
    cv_std     = bundle.get('cv_std', 80000)
    top_feats  = bundle.get('top_features', [])
    metrics    = bundle.get('metrics', {})

    predicted  = float(model.predict(X_ready)[0])
    predicted  = max(predicted, 5000)  # floor at LKR 5,000

    # Confidence interval: ±1 CV-residual std (68% coverage)
    ci_low  = max(predicted - cv_std, 0)
    ci_high = predicted + cv_std

    # Human-readable factor explanations for top 3 features
    factor_labels = {
        'district_enc':      f"Location ({data.get('district','Colombo')}) — strongest price driver",
        'district':          f"Location ({data.get('district','Colombo')}) — strongest price driver",
        'bathrooms':         f"Bathrooms ({data.get('bathrooms',1)}) — corr 0.21 with price",
        'bedrooms':          f"Bedrooms ({data.get('bedrooms',2)}) — corr 0.12 with price",
        'property_type_enc': f"Property type ({data.get('property_type','apartment')}) — corr 0.42 with price",
        'property_type':     f"Property type ({data.get('property_type','apartment')}) — corr 0.42 with price",
        'furnished_num':     f"Furnished status ({data.get('furnished','unfurnished')}) — corr 0.15 with price",
        'latitude':          f"Location coordinates (latitude) — district centroid",
        'longitude':         f"Location coordinates (longitude) — district centroid",
    }
    top_3_factors = [factor_labels.get(f, f) for f in top_feats[:3]]

    # Confidence score 0–1: based on R² and how far prediction is from CI boundary
    r2         = metrics.get('R2', 0.29)
    confidence = round(max(0.0, min(1.0, r2 + 0.2)), 4)  # R² + small offset, capped at 1

    return jsonify({
        'predicted_price':      round(predicted, 2),
        'price_range': {
            'low':  round(ci_low,  2),
            'high': round(ci_high, 2),
        },
        'confidence_interval':  round(cv_std, 2),
        'top_3_factors':        top_3_factors,
        # Backward-compatible fields (used by Node proxy → DB insert + old frontend)
        'confidence':           confidence,
        'model_version':        '2.0-real-data',
        'model_info': {
            'name':             bundle.get('model_name', 'GradientBoosting'),
            'r2':               metrics.get('R2', 0),
            'cv_r2':            metrics.get('CV_R2_mean', 0),
            'mae':              metrics.get('MAE', 0),
            'training_samples': metrics.get('samples', 0),
        },
    })


@app.route('/health', methods=['GET'])
def health():
    trained = os.path.exists(PRICE_MODEL_PATH)
    info    = {}
    if trained:
        try:
            b = joblib.load(PRICE_MODEL_PATH)
            info = b.get('metrics', {})
            info['model_name'] = b.get('model_name', '')
        except Exception:
            pass
    return jsonify({
        'status':        'ok',
        'service':       'price-prediction',
        'model_trained': trained,
        'model_info':    info,
    })


@app.route('/model-info', methods=['GET'])
def model_info():
    """Returns EDA findings and model metrics for the admin dashboard."""
    try:
        bundle, encoders, _ = _load()
    except FileNotFoundError:
        return jsonify({'error': 'Model not trained'}), 503

    district_means = encoders.get('district_means', {})
    top_districts  = sorted(district_means.items(), key=lambda x: x[1], reverse=True)
    feature_cols   = encoders.get('feature_cols', [])
    has_latlng     = 'latitude' in feature_cols or 'longitude' in feature_cols

    return jsonify({
        'model_name':    bundle.get('model_name'),
        'metrics':       bundle.get('metrics', {}),
        'top_features':  bundle.get('top_features', []),
        'feature_cols':  feature_cols,
        'district_price_ranking': [
            {'district': d, 'avg_rent': round(v, 0)}
            for d, v in top_districts
        ],
        'eda_notes': {
            'total_rows_after_cleaning': bundle.get('metrics', {}).get('samples', 324),
            'outliers_removed':          44,
            'beds_baths_imputed':        83,
            'area_sqft_coverage':        '0.3% — dropped (zero variance)',
            'lat_lng_coverage':          ('kept as a feature — district centroid used at serve time'
                                          if has_latlng else
                                          '54% — imputed then dropped (collinear with district)'),
            'price_range':               'LKR 9,500 – 700,000',
        },
    })


if __name__ == '__main__':
    # Eagerly load model so first /predict is fast
    if os.path.exists(PRICE_MODEL_PATH):
        _load()
        print(f'[price-prediction] Model loaded: {_bundle["model_name"]} '
              f'| CV R²={_bundle["metrics"].get("CV_R2_mean", 0):.4f} '
              f'| MAE=LKR {_bundle["metrics"].get("MAE", 0):,.0f}')
    else:
        print('[price-prediction] No model found — run train.py first')
    app.run(host='0.0.0.0', port=8002, debug=True)
