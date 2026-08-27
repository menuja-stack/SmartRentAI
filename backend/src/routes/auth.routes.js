const router = require('express').Router();
const { body } = require('express-validator');
const { register, login, getMe, changePassword } = require('../controllers/auth.controller');
const { authenticate } = require('../middleware/auth.middleware');

router.post('/register',
  body('full_name').trim().isLength({ min: 2, max: 100 }),
  body('email').isEmail().normalizeEmail(),
  body('password').isLength({ min: 6 }),
  body('role').optional().isIn(['renter', 'landlord']),
  register
);

router.post('/login',
  body('email').isEmail().normalizeEmail(),
  body('password').notEmpty(),
  login
);

router.get('/me', authenticate, getMe);

router.put('/change-password',
  authenticate,
  body('current_password').notEmpty(),
  body('new_password').isLength({ min: 6 }),
  changePassword
);

module.exports = router;
