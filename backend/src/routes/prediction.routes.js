const router = require('express').Router();
const { predictPrice, getPredictionHistory } = require('../controllers/prediction.controller');
const { authenticate } = require('../middleware/auth.middleware');

router.post('/price',    predictPrice);
router.get('/history',   authenticate, getPredictionHistory);

module.exports = router;
