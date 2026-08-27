const router = require('express').Router();
const axios  = require('axios');

const AI_URL = () => process.env.AI_LOCATION_URL || 'http://localhost:8004';

// GET /api/location/score/:district
router.get('/score/:district', async (req, res) => {
  try {
    const { data } = await axios.get(`${AI_URL()}/score/${req.params.district}`, { timeout: 10000 });
    res.json(data);
  } catch (err) {
    if (err.code === 'ECONNREFUSED') {
      return res.status(503).json({ error: 'Location intelligence service offline' });
    }
    res.status(500).json({ error: 'Failed to fetch location score' });
  }
});

// GET /api/location/all
router.get('/all', async (req, res) => {
  try {
    const { data } = await axios.get(`${AI_URL()}/score/all`, { timeout: 15000 });
    res.json(data);
  } catch (err) {
    res.status(503).json({ error: 'Location intelligence service offline' });
  }
});

// POST /api/location/compare
router.post('/compare', async (req, res) => {
  try {
    const { data } = await axios.post(`${AI_URL()}/compare`, req.body, { timeout: 10000 });
    res.json(data);
  } catch {
    res.status(503).json({ error: 'Location intelligence service offline' });
  }
});

// POST /api/location/predict-live
router.post('/predict-live', async (req, res) => {
  try {
    const { data } = await axios.post(`${AI_URL()}/predict-live`, req.body, { timeout: 10000 });
    res.json(data);
  } catch {
    res.status(503).json({ error: 'Service offline' });
  }
});

module.exports = router;
