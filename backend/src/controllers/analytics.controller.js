const { pool } = require('../config/db');

// GET /api/analytics/dashboard  (admin only)
async function getDashboard(req, res) {
  try {
    const [[users]]       = await pool.query('SELECT COUNT(*) AS total FROM users');
    const [[properties]]  = await pool.query('SELECT COUNT(*) AS total FROM properties WHERE status="available"');
    const [[predictions]] = await pool.query('SELECT COUNT(*) AS total FROM rental_predictions');
    const [[chats]]       = await pool.query('SELECT COUNT(*) AS total FROM chatbot_sessions');

    const [roleBreakdown] = await pool.query(
      'SELECT role, COUNT(*) AS count FROM users GROUP BY role'
    );

    const [topCities] = await pool.query(`
      SELECT l.city, COUNT(p.id) AS listings, AVG(p.monthly_rent) AS avg_rent
      FROM properties p JOIN locations l ON p.location_id = l.id
      WHERE p.status = 'available'
      GROUP BY l.city ORDER BY listings DESC LIMIT 10
    `);

    const [rentTrend] = await pool.query(`
      SELECT DATE_FORMAT(created_at, '%Y-%m') AS month,
             AVG(monthly_rent) AS avg_rent, COUNT(*) AS new_listings
      FROM properties
      GROUP BY month ORDER BY month DESC LIMIT 12
    `);

    const [recentActivity] = await pool.query(`
      SELECT event_type, COUNT(*) AS count, DATE(created_at) AS day
      FROM analytics_logs
      WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
      GROUP BY event_type, day ORDER BY day DESC
    `);

    res.json({
      stats: {
        total_users:       users.total,
        total_properties:  properties.total,
        total_predictions: predictions.total,
        total_chats:       chats.total,
      },
      role_breakdown:  roleBreakdown,
      top_cities:      topCities,
      rent_trend:      rentTrend.reverse(),
      recent_activity: recentActivity,
    });
  } catch (err) {
    console.error('analytics error:', err);
    res.status(500).json({ error: 'Server error' });
  }
}

// POST /api/analytics/log  — log events from frontend
async function logEvent(req, res) {
  const { event_type, property_id, meta } = req.body;
  try {
    await pool.query(
      'INSERT INTO analytics_logs (event_type, user_id, property_id, meta, ip_address) VALUES (?,?,?,?,?)',
      [event_type, req.user?.id || null, property_id || null, JSON.stringify(meta || {}), req.ip]
    );
    res.json({ ok: true });
  } catch {
    res.json({ ok: false });
  }
}

module.exports = { getDashboard, logEvent };
