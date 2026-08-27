require('dotenv').config();
const express    = require('express');
const cors       = require('cors');
const helmet     = require('helmet');
const morgan     = require('morgan');
const path       = require('path');
const rateLimit  = require('express-rate-limit');

const { testConnection } = require('./config/db');
const authRoutes         = require('./routes/auth.routes');
const propertyRoutes     = require('./routes/property.routes');
const recommendRoutes    = require('./routes/recommendation.routes');
const predictionRoutes   = require('./routes/prediction.routes');
const chatbotRoutes      = require('./routes/chatbot.routes');
const analyticsRoutes    = require('./routes/analytics.routes');
const adminRoutes        = require('./routes/admin.routes');
const userRoutes         = require('./routes/user.routes');
const locationRoutes     = require('./routes/location.routes');
const locationsRoutes    = require('./routes/locations.routes');
const scraperRoutes      = require('./routes/scraper.routes');

const app = express();

// ── Security middleware ──────────────────────────────────────
app.use(helmet());
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true,
}));

// ── Rate limiting ────────────────────────────────────────────
// Strict only on auth (brute-force protection)
app.use('/api/auth', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 50,
  message: { error: 'Too many login attempts, please try again later.' },
}));

// General limit — high enough for normal development use
// Skip admin/analytics/scraper so the dashboard never gets blocked
app.use('/api', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5000,
  skip: (req) =>
    req.path.startsWith('/analytics') ||
    req.path.startsWith('/admin') ||
    req.path.startsWith('/scraper'),
}));

// ── General middleware ───────────────────────────────────────
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(morgan('dev'));

// ── Static files (uploaded images) ──────────────────────────
// Override Helmet's Cross-Origin-Resource-Policy: same-origin so the React
// dev server on :3000 can load images served from the API on :5000.
app.use('/uploads', (req, res, next) => {
  res.setHeader('Cross-Origin-Resource-Policy', 'cross-origin');
  next();
}, express.static(path.join(__dirname, '..', 'uploads')));

// ── Health check ─────────────────────────────────────────────
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'SmartRentAI API', version: '1.0.0' });
});

// ── Routes ───────────────────────────────────────────────────
app.use('/api/auth',            authRoutes);
app.use('/api/properties',      propertyRoutes);
app.use('/api/recommendations', recommendRoutes);
app.use('/api/predictions',     predictionRoutes);
app.use('/api/chatbot',         chatbotRoutes);
app.use('/api/analytics',       analyticsRoutes);
app.use('/api/admin',           adminRoutes);
app.use('/api/users',           userRoutes);
app.use('/api/location',        locationRoutes);
app.use('/api/locations',       locationsRoutes);
app.use('/api/scraper',         scraperRoutes);

// ── 404 handler ──────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// ── Global error handler ─────────────────────────────────────
app.use((err, req, res, next) => {
  console.error(err.stack);
  const status = err.status || 500;
  res.status(status).json({
    error: process.env.NODE_ENV === 'production'
      ? 'Internal server error'
      : err.message,
  });
});

// ── Start ─────────────────────────────────────────────────────
const PORT = process.env.PORT || 5000;
testConnection().then(() => {
  app.listen(PORT, () => {
    console.log(`🚀 SmartRentAI API running on http://localhost:${PORT}`);
  });
});
