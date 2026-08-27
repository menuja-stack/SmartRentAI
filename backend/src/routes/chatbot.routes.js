const router = require('express').Router();
const { sendMessage, getHistory } = require('../controllers/chatbot.controller');
const { authenticate } = require('../middleware/auth.middleware');

router.post('/message',           sendMessage);
router.get('/history/:session_id', authenticate, getHistory);

module.exports = router;
