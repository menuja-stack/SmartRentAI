const router = require('express').Router();
const { getRecommendations, getProfileInsights, getSimilar } = require('../controllers/recommendation.controller');
const { authenticate } = require('../middleware/auth.middleware');

router.get('/',             authenticate, getRecommendations);
router.get('/insights',     authenticate, getProfileInsights);
router.get('/similar/:id',  getSimilar);

module.exports = router;
