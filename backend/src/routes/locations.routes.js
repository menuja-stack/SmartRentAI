const router = require('express').Router();
const { pool } = require('../config/db');

// GET /api/locations/search?q=bor
// Autocomplete for town/city + district search against the locations table.
// Returns distinct { city, district } pairs, best matches first.
router.get('/search', async (req, res) => {
  const q = (req.query.q || '').trim();
  if (q.length < 1) return res.json([]);

  try {
    const like   = `%${q}%`;
    const prefix = `${q}%`;
    const [rows] = await pool.query(
      `SELECT DISTINCT city, district
         FROM locations
        WHERE city LIKE ? OR district LIKE ?
        ORDER BY (city = ?) DESC,        -- exact city match first
                 (city LIKE ?) DESC,     -- then city prefix matches
                 city ASC
        LIMIT 10`,
      [like, like, q, prefix]
    );
    res.json(rows);
  } catch (err) {
    console.error('locations/search error:', err);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
