const bcrypt  = require('bcryptjs');
const jwt     = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');
const { pool } = require('../config/db');
const { validationResult } = require('express-validator');

function signToken(user) {
  return jwt.sign(
    { id: user.id, email: user.email, role: user.role },
    process.env.JWT_SECRET,
    { expiresIn: process.env.JWT_EXPIRES_IN || '7d' }
  );
}

// POST /api/auth/register
async function register(req, res) {
  const errors = validationResult(req);
  if (!errors.isEmpty()) return res.status(422).json({ errors: errors.array() });

  const { full_name, email, password, role = 'renter' } = req.body;

  try {
    const [existing] = await pool.query('SELECT id FROM users WHERE email = ?', [email]);
    if (existing.length) return res.status(409).json({ error: 'Email already registered' });

    const hash  = await bcrypt.hash(password, 10);
    const token = uuidv4();

    const [result] = await pool.query(
      `INSERT INTO users (full_name, email, password_hash, role, verify_token, is_verified)
       VALUES (?, ?, ?, ?, ?, 1)`,
      [full_name, email, hash, role, token]
    );

    const user = { id: result.insertId, email, role };
    res.status(201).json({
      message: 'Registration successful',
      token:   signToken(user),
      user:    { id: user.id, full_name, email, role },
    });
  } catch (err) {
    console.error('register error:', err);
    res.status(500).json({ error: 'Server error' });
  }
}

// POST /api/auth/login
async function login(req, res) {
  const errors = validationResult(req);
  if (!errors.isEmpty()) return res.status(422).json({ errors: errors.array() });

  const { email, password } = req.body;

  try {
    const [rows] = await pool.query(
      'SELECT id, full_name, email, password_hash, role, avatar_url FROM users WHERE email = ?',
      [email]
    );
    if (!rows.length) return res.status(401).json({ error: 'Invalid credentials' });

    const user = rows[0];
    const match = await bcrypt.compare(password, user.password_hash);
    if (!match) return res.status(401).json({ error: 'Invalid credentials' });

    await pool.query('UPDATE users SET last_login = NOW() WHERE id = ?', [user.id]);

    res.json({
      token: signToken(user),
      user: {
        id:         user.id,
        full_name:  user.full_name,
        email:      user.email,
        role:       user.role,
        avatar_url: user.avatar_url,
      },
    });
  } catch (err) {
    console.error('login error:', err);
    res.status(500).json({ error: 'Server error' });
  }
}

// GET /api/auth/me
async function getMe(req, res) {
  try {
    const [rows] = await pool.query(
      'SELECT id, full_name, email, role, avatar_url, phone, created_at FROM users WHERE id = ?',
      [req.user.id]
    );
    if (!rows.length) return res.status(404).json({ error: 'User not found' });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
}

// PUT /api/auth/change-password
async function changePassword(req, res) {
  const { current_password, new_password } = req.body;
  try {
    const [rows] = await pool.query('SELECT password_hash FROM users WHERE id = ?', [req.user.id]);
    if (!rows.length) return res.status(404).json({ error: 'User not found' });

    const match = await bcrypt.compare(current_password, rows[0].password_hash);
    if (!match) return res.status(400).json({ error: 'Current password incorrect' });

    const hash = await bcrypt.hash(new_password, 10);
    await pool.query('UPDATE users SET password_hash = ? WHERE id = ?', [hash, req.user.id]);

    res.json({ message: 'Password updated successfully' });
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
}

module.exports = { register, login, getMe, changePassword };
