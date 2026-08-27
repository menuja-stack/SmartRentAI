const router = require('express').Router();
const { getDashboard, logEvent } = require('../controllers/analytics.controller');
const { authenticate, authorize } = require('../middleware/auth.middleware');

router.get('/dashboard', authenticate, authorize('admin'), getDashboard);
router.post('/log',      logEvent);

module.exports = router;
