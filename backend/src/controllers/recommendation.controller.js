const axios  = require('axios');
const { pool } = require('../config/db');

const AI_URL = () => process.env.AI_RECOMMENDATION_URL || 'http://localhost:8001';

// Build the flat profile the recommendation service expects from a prefs row.
function buildProfile(userId, prefs) {
  return {
    user_id:            userId,
    profession:         prefs.profession,
    age_group:          prefs.age_group,
    family_size:        prefs.family_size,
    has_children:       prefs.has_children,
    has_vehicle:        prefs.has_vehicle,
    current_district:   prefs.current_district,
    budget:             prefs.current_rent_budget || prefs.max_budget,
    priority_safety:    prefs.priority_safety,
    priority_price:     prefs.priority_price,
    priority_transport: prefs.priority_transport,
    priority_hospital:  prefs.priority_hospital,
    priority_space:     prefs.priority_space,
    preferred_type:     prefs.preferred_property_type || prefs.property_type,
    preferred_districts: prefs.preferred_districts,
    top_k: 12,
  };
}

// GET /api/recommendations  — profile-based "For You" for the logged-in user
async function getRecommendations(req, res) {
  try {
    const [prefsRows] = await pool.query('SELECT * FROM user_preferences WHERE user_id = ?', [req.user.id]);
    const prefs = prefsRows[0];

    // No profile yet → tell the client to show the onboarding prompt
    if (!prefs || !prefs.profession) {
      return res.json({ needs_onboarding: true, recommendations: [], profile_summary: null });
    }

    let svc;
    try {
      const { data } = await axios.post(`${AI_URL()}/recommend`, buildProfile(req.user.id, prefs), { timeout: 12000 });
      svc = data;
    } catch (e) {
      if (e.code === 'ECONNREFUSED') {
        return res.status(503).json({ error: 'Recommendation service offline', recommendations: [] });
      }
      throw e;
    }

    const ranked = svc.recommendations || [];
    const topIds = ranked.map(r => r.property_id);
    if (!topIds.length) {
      return res.json({ needs_onboarding: false, recommendations: [], profile_summary: svc.profile_summary });
    }

    // Enrich with full property details (image, etc.), preserving service order
    const [full] = await pool.query(`
      SELECT p.*, l.city, l.district,
             (SELECT url FROM property_images WHERE property_id = p.id AND is_primary = 1 LIMIT 1) AS primary_image,
             (SELECT AVG(rating) FROM reviews WHERE property_id = p.id) AS avg_rating
      FROM properties p
      JOIN locations l ON p.location_id = l.id
      WHERE p.id IN (${topIds.map(() => '?').join(',')})
    `, topIds);

    const fullMap = Object.fromEntries(full.map(p => [p.id, p]));
    const recommendations = ranked
      .filter(r => fullMap[r.property_id])
      .map(r => ({
        ...fullMap[r.property_id],
        match_score:    r.match_score,
        match_reasons:  r.match_reasons,
        saferent_score: r.saferent_score,
      }));

    res.json({
      needs_onboarding: false,
      profile_summary:  svc.profile_summary,
      criteria:         svc.criteria,
      recommendations,
    });
  } catch (err) {
    console.error('getRecommendations error:', err);
    res.status(500).json({ error: 'Server error' });
  }
}

// GET /api/recommendations/insights  — what the model inferred for this user
async function getProfileInsights(req, res) {
  try {
    const { data } = await axios.get(
      `${AI_URL()}/recommend/profile-insights/${req.user.id}`, { timeout: 10000 });
    res.json(data);
  } catch (e) {
    if (e.response?.status === 404) return res.status(404).json({ error: 'No profile yet' });
    if (e.code === 'ECONNREFUSED')  return res.status(503).json({ error: 'Recommendation service offline' });
    res.status(500).json({ error: 'Server error' });
  }
}

// GET /api/recommendations/similar/:id  — similar properties
async function getSimilar(req, res) {
  try {
    const [target] = await pool.query(
      'SELECT * FROM properties WHERE id = ?', [req.params.id]
    );
    if (!target.length) return res.status(404).json({ error: 'Property not found' });

    const p = target[0];
    const [rows] = await pool.query(`
      SELECT p2.*, l.city, l.district,
             (SELECT url FROM property_images WHERE property_id = p2.id AND is_primary = 1 LIMIT 1) AS primary_image
      FROM properties p2
      JOIN locations l ON p2.location_id = l.id
      WHERE p2.id != ?
        AND p2.status = 'available'
        AND p2.location_id = ?
        AND p2.property_type = ?
      ORDER BY ABS(p2.monthly_rent - ?) ASC
      LIMIT 6
    `, [p.id, p.location_id, p.property_type, p.monthly_rent]);

    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
}

module.exports = { getRecommendations, getProfileInsights, getSimilar };
