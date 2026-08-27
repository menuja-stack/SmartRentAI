"""
SmartRentAI — Profile-Based Recommendation Engine (Phase 5)
===========================================================
Two-stage hybrid:
  Stage 1  profile  -> ideal criteria   (RandomForest, trained on 10k synthetic)
  Stage 2  criteria -> properties        (priority-weighted cosine similarity)

Run:  python app.py            (port 8001)
Pre-req: run generate_dataset.py, build_property_features.py, train_profile_model.py
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS

import recommender

app = Flask(__name__)
CORS(app)


@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Body: a user profile (profession, age_group, family_size, has_children,
          has_vehicle, current_district, budget, priority_*, preferred_type,
          preferred_districts). Missing priorities are cold-started from
          profession defaults.
    """
    profile = request.get_json(silent=True) or {}
    if not os.path.exists(recommender.MODEL_PATH):
        return jsonify({'error': 'Model not trained. Run train_profile_model.py first.'}), 503
    try:
        top_k = int(profile.get('top_k', 10))
        result = recommender.recommend(profile, top_k=top_k)
        return jsonify(result)
    except Exception as e:
        app.logger.exception('recommend failed')
        return jsonify({'error': f'Recommendation failed: {e}'}), 500


@app.route('/recommend/profile-insights/<int:user_id>', methods=['GET'])
def profile_insights(user_id):
    """Show WHAT the model inferred as ideal criteria for this user."""
    if not os.path.exists(recommender.MODEL_PATH):
        return jsonify({'error': 'Model not trained.'}), 503

    profile = recommender.fetch_user_profile(user_id)
    if not profile:
        return jsonify({'error': 'No saved profile for this user'}), 404

    bundle, _ = recommender.load()
    p = recommender.apply_cold_start(profile)
    crit = recommender.predict_criteria(bundle, p)
    return jsonify({
        'user_id':           user_id,
        'inferred_criteria': crit,
        'explanation':       recommender.criteria_explanation(crit, p),
        'profile_summary':   recommender._summary(p, crit),
        'priorities_used': {
            'safety':    p['priority_safety'],    'price':    p['priority_price'],
            'transport': p['priority_transport'], 'hospital': p['priority_hospital'],
            'space':     p['priority_space'],
        },
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status':  'ok',
        'service': 'recommendation',
        'model_trained': os.path.exists(recommender.MODEL_PATH),
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)
