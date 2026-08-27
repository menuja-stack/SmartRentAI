const router = require('express').Router();
const { body } = require('express-validator');
const ctrl   = require('../controllers/property.controller');
const { authenticate, authorize } = require('../middleware/auth.middleware');
const upload = require('../middleware/upload.middleware');

router.get('/',          ctrl.getProperties);
router.get('/saved',     authenticate, ctrl.getSaved);
router.get('/:id',       ctrl.getProperty);

router.post('/',
  authenticate,
  authorize('landlord', 'admin'),
  upload.array('images', 10),
  body('title').trim().isLength({ min: 5, max: 200 }).withMessage('Title must be 5–200 characters'),
  body('description').trim().isLength({ min: 10 }).withMessage('Description must be at least 10 characters'),
  body('property_type').isIn(['apartment','house','room','villa','commercial']).withMessage('Invalid property type'),
  body('bedrooms').isInt({ min: 0, max: 20 }).withMessage('Bedrooms must be 0–20'),
  body('bathrooms').isInt({ min: 0, max: 20 }).withMessage('Bathrooms must be 0–20'),
  body('monthly_rent').isFloat({ min: 1 }).withMessage('Monthly rent is required'),
  body('address_line').trim().notEmpty().withMessage('Address is required'),
  body('city').trim().notEmpty().withMessage('City is required'),
  body('district').trim().notEmpty().withMessage('District is required'),
  ctrl.createProperty
);

router.put('/:id',  authenticate, ctrl.updateProperty);
router.delete('/:id', authenticate, ctrl.deleteProperty);
router.post('/:id/save', authenticate, ctrl.toggleSave);

module.exports = router;
