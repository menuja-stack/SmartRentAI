const axios    = require('axios');
const { pool } = require('../config/db');

const AI_URL = () => process.env.AI_PRICE_URL || 'http://localhost:8002';

// POST /api/predictions/price
async function predictPrice(req, res) {
  const features = req.body;

  try {
    const { data } = await axios.post(`${AI_URL()}/predict`, features, { timeout: 10000 });

    // Save prediction log
    await pool.query(
      `INSERT INTO rental_predictions (user_id, input_features, predicted_price, confidence, model_version)
       VALUES (?, ?, ?, ?, ?)`,
      [
        req.user?.id || null,
        JSON.stringify(features),
        data.predicted_price,
        data.confidence || null,
        data.model_version || '1.0',
      ]
    );

    res.json(data);
  } catch (err) {
    if (err.code === 'ECONNREFUSED') {
      // AI service offline — return simple heuristic
      const base = (features.bedrooms || 2) * 15000 + (features.bathrooms || 1) * 5000;
      return res.json({
        predicted_price: base,
        confidence:      0.5,
        model_version:   'heuristic',
        note:            'AI service offline, using heuristic estimate',
      });
    }
    console.error('predictPrice error:', err);
    res.status(500).json({ error: 'Prediction failed' });
  }
}

// GET /api/predictions/history
async function getPredictionHistory(req, res) {
  try {
    const [rows] = await pool.query(
      `SELECT id, input_features, predicted_price, confidence, model_version, created_at
       FROM rental_predictions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20`,
      [req.user.id]
    );
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
}

module.exports = { predictPrice, getPredictionHistory };
