const router   = require('express').Router();
const { pool } = require('../config/db');
const { authenticate } = require('../middleware/auth.middleware');

router.use(authenticate);

// GET /api/users/preferences
router.get('/preferences', async (req, res) => {
  const [rows] = await pool.query('SELECT * FROM user_preferences WHERE user_id = ?', [req.user.id]);
  res.json(rows[0] || {});
});

// PUT /api/users/preferences
// Accepts the full extended profile (legacy fields + Phase-1 onboarding fields).
// Only columns present in the whitelist are written, so partial saves work
// (e.g. saving just the lifestyle priorities from step 3).
router.put('/preferences', async (req, res) => {
  // Whitelist of writable columns
  const COLS = [
    // legacy
    'preferred_city', 'min_budget', 'max_budget', 'bedrooms', 'property_type', 'furnished_pref',
    // personal
    'profession', 'age_group', 'family_size', 'has_children', 'has_vehicle',
    // current situation
    'current_district', 'current_city', 'current_rent_budget',
    'preferred_districts', 'preferred_property_type',
    // lifestyle priorities
    'priority_safety', 'priority_price', 'priority_transport', 'priority_hospital', 'priority_space',
    // bookkeeping
    'onboarding_completed',
  ];

  const present = COLS.filter(c => req.body[c] !== undefined);
  if (!present.length) return res.status(400).json({ error: 'No valid preference fields provided' });

  // preferred_districts may arrive as an array → store CSV
  const normalize = (col, v) => {
    if (col === 'preferred_districts' && Array.isArray(v)) return v.slice(0, 3).join(',');
    if ((col === 'has_children' || col === 'has_vehicle' || col === 'onboarding_completed'))
      return v ? 1 : 0;
    if (v === '' ) return null;
    return v;
  };

  const insertCols = ['user_id', ...present];
  const placeholders = insertCols.map(() => '?').join(',');
  const insertVals = [req.user.id, ...present.map(c => normalize(c, req.body[c]))];
  const updateClause = present.map(c => `${c} = VALUES(${c})`).join(', ');

  await pool.query(
    `INSERT INTO user_preferences (${insertCols.join(',')}) VALUES (${placeholders})
     ON DUPLICATE KEY UPDATE ${updateClause}`,
    insertVals
  );
  res.json({ message: 'Preferences saved' });
});

// POST /api/users/activity  — implicit feedback signal (Phase 7)
// Records view / save / enquiry actions to search_history so the preference-
// learning job can re-weight the user's lifestyle priorities over time.
router.post('/activity', async (req, res) => {
  const { property_id, action } = req.body;
  const ALLOWED = ['view', 'save', 'enquiry'];
  if (!property_id || !ALLOWED.includes(action)) {
    return res.status(400).json({ error: 'Invalid activity' });
  }
  try {
    await pool.query(
      'INSERT INTO search_history (user_id, query, property_id, action) VALUES (?,?,?,?)',
      [req.user.id, `${action}:${property_id}`, property_id, action]
    );
    res.json({ logged: true });
  } catch (err) {
    console.error('activity log error:', err);
    res.status(500).json({ error: 'Server error' });
  }
});

// PUT /api/users/profile
router.put('/profile', async (req, res) => {
  const { full_name, phone } = req.body;
  await pool.query('UPDATE users SET full_name = ?, phone = ? WHERE id = ?',
    [full_name, phone, req.user.id]);
  res.json({ message: 'Profile updated' });
});

module.exports = router;
