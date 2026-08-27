const axios    = require('axios');
const { pool } = require('../config/db');
const { v4: uuidv4 } = require('uuid');

const AI_URL = () => process.env.AI_CHATBOT_URL || 'http://localhost:8003';

// POST /api/chatbot/message
async function sendMessage(req, res) {
  const { message, session_id } = req.body;
  if (!message?.trim()) return res.status(400).json({ error: 'Message is required' });

  const sid = session_id || uuidv4();

  try {
    // Ensure session exists
    await pool.query(
      'INSERT IGNORE INTO chatbot_sessions (session_id, user_id) VALUES (?, ?)',
      [sid, req.user?.id || null]
    );

    // Log user message
    await pool.query(
      'INSERT INTO chatbot_messages (session_id, role, message) VALUES (?,?,?)',
      [sid, 'user', message]
    );

    // Fetch last 6 messages for context
    const [history] = await pool.query(
      `SELECT role, message FROM chatbot_messages WHERE session_id = ?
       ORDER BY created_at DESC LIMIT 6`,
      [sid]
    );

    let botReply, intent, confidence;
    try {
      const { data } = await axios.post(
        `${AI_URL()}/chat`,
        { message, history: history.reverse(), session_id: sid },
        { timeout: 8000 }
      );
      botReply   = data.reply;
      intent     = data.intent;
      confidence = data.confidence;
    } catch {
      botReply = getFallbackReply(message);
      intent   = 'fallback';
    }

    // Log bot reply
    await pool.query(
      'INSERT INTO chatbot_messages (session_id, role, message, intent, confidence) VALUES (?,?,?,?,?)',
      [sid, 'bot', botReply, intent, confidence || null]
    );

    res.json({ reply: botReply, session_id: sid, intent });
  } catch (err) {
    console.error('chatbot error:', err);
    res.status(500).json({ error: 'Server error' });
  }
}

// GET /api/chatbot/history/:session_id
async function getHistory(req, res) {
  try {
    const [rows] = await pool.query(
      'SELECT role, message, created_at FROM chatbot_messages WHERE session_id = ? ORDER BY created_at ASC',
      [req.params.session_id]
    );
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
}

function getFallbackReply(message) {
  const msg = message.toLowerCase();
  if (msg.includes('price') || msg.includes('rent') || msg.includes('cost')) {
    return 'Rental prices vary by location. Use our Price Prediction tool for an accurate estimate based on property features.';
  }
  if (msg.includes('recommend') || msg.includes('suggest')) {
    return 'Visit your Recommendations page for AI-powered property suggestions tailored to your preferences.';
  }
  if (msg.includes('contact') || msg.includes('landlord')) {
    return 'You can contact the landlord directly from the property details page using the enquiry form.';
  }
  return "I'm here to help with your rental search! Try asking about property prices, recommendations, or how to contact a landlord.";
}

module.exports = { sendMessage, getHistory };
