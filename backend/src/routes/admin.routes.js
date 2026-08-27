const router = require('express').Router();
const { pool } = require('../config/db');
const { authenticate, authorize } = require('../middleware/auth.middleware');

router.use(authenticate, authorize('admin'));

// GET all users
router.get('/users', async (req, res) => {
  const [rows] = await pool.query(
    'SELECT id, full_name, email, role, is_verified, created_at FROM users ORDER BY created_at DESC'
  );
  res.json(rows);
});

// PATCH user role
router.patch('/users/:id/role', async (req, res) => {
  const { role } = req.body;
  if (!['renter','landlord','admin'].includes(role)) return res.status(400).json({ error: 'Invalid role' });
  await pool.query('UPDATE users SET role = ? WHERE id = ?', [role, req.params.id]);
  res.json({ message: 'Role updated' });
});

// DELETE user
router.delete('/users/:id', async (req, res) => {
  await pool.query('DELETE FROM users WHERE id = ?', [req.params.id]);
  res.json({ message: 'User deleted' });
});

// GET all properties (admin view)
router.get('/properties', async (req, res) => {
  const [rows] = await pool.query(`
    SELECT p.id, p.title, p.monthly_rent, p.status, p.created_at,
           u.full_name AS landlord, l.city
    FROM properties p
    JOIN users u ON p.landlord_id = u.id
    JOIN locations l ON p.location_id = l.id
    ORDER BY p.created_at DESC
  `);
  res.json(rows);
});

// PATCH property status
router.patch('/properties/:id/status', async (req, res) => {
  const { status } = req.body;
  if (!['available','rented','inactive'].includes(status)) return res.status(400).json({ error: 'Invalid status' });
  await pool.query('UPDATE properties SET status = ? WHERE id = ?', [status, req.params.id]);
  res.json({ message: 'Status updated' });
});

module.exports = router;
