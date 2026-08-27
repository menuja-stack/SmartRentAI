const router   = require('express').Router();
const path     = require('path');
const { spawn } = require('child_process');
const { pool } = require('../config/db');
const { authenticate, authorize } = require('../middleware/auth.middleware');

router.use(authenticate, authorize('admin'));

// ── Scraper job runner ───────────────────────────────────────────────────────
// Project root (…/SmartRentAI) — two levels up from src/routes.
const PROJECT_ROOT = path.resolve(__dirname, '..', '..', '..');
const SCRAPER_REL  = path.join('ai-services', 'scraper', 'scraper.py');
const PYTHON       = process.env.PYTHON_BIN || 'python';

const VALID_SITES = ['all', 'ikman', 'houselk'];
const VALID_DISTRICTS = new Set([
  'all', 'Colombo', 'Gampaha', 'Kalutara', 'Kandy', 'Matale', 'Nuwara Eliya',
  'Galle', 'Matara', 'Hambantota', 'Jaffna', 'Kilinochchi', 'Mannar', 'Mullaitivu',
  'Vavuniya', 'Trincomalee', 'Batticaloa', 'Ampara', 'Kurunegala', 'Puttalam',
  'Anuradhapura', 'Polonnaruwa', 'Badulla', 'Monaragala', 'Ratnapura', 'Kegalle',
]);

// Single in-memory job (one scrape at a time)
let job = {
  running: false, startedAt: null, finishedAt: null,
  args: null, code: null, saved: null, skipped: null, error: null, tail: [],
};

const pushLine = (line) => {
  job.tail.push(line);
  if (job.tail.length > 40) job.tail.shift();   // keep last 40 lines
};

// POST /api/scraper/run  { pages, district, site, noImages }
router.post('/run', (req, res) => {
  if (job.running) {
    return res.status(409).json({ error: 'A scrape is already running', job });
  }

  // ── Validate & sanitise (spawn uses an args array → no shell injection) ──
  let pages = parseInt(req.body.pages, 10);
  if (Number.isNaN(pages)) pages = 2;
  pages = Math.max(1, Math.min(5, pages));               // cap to keep runs sane

  const district = VALID_DISTRICTS.has(req.body.district) ? req.body.district : 'all';
  const site     = VALID_SITES.includes(req.body.site) ? req.body.site : 'all';
  const noImages = !!req.body.noImages;

  const args = ['-u', SCRAPER_REL, '--pages', String(pages), '--site', site];
  if (district !== 'all') args.push('--district', district);
  if (noImages) args.push('--no-images');

  // Reset job state
  job = {
    running: true, startedAt: new Date().toISOString(), finishedAt: null,
    args: { pages, district, site, noImages }, code: null,
    saved: null, skipped: null, error: null, tail: [],
  };

  let child;
  try {
    child = spawn(PYTHON, args, { cwd: PROJECT_ROOT });
  } catch (e) {
    job.running = false;
    job.error = `Failed to start python: ${e.message}`;
    return res.status(500).json({ error: job.error });
  }

  const onData = (buf) => buf.toString().split(/\r?\n/).forEach(l => l.trim() && pushLine(l));
  child.stdout.on('data', onData);
  child.stderr.on('data', onData);     // python logging writes to stderr

  child.on('error', (e) => {
    job.running = false; job.finishedAt = new Date().toISOString();
    job.error = e.code === 'ENOENT'
      ? 'Python not found on PATH (set PYTHON_BIN in backend/.env)'
      : e.message;
  });

  child.on('close', (code) => {
    job.running = false;
    job.finishedAt = new Date().toISOString();
    job.code = code;
    const all = job.tail.join('\n');
    const m = all.match(/saved:\s*(\d+),\s*skipped[^:]*:\s*(\d+)/i);
    if (m) { job.saved = Number(m[1]); job.skipped = Number(m[2]); }
    if (code !== 0 && !job.error) job.error = `Scraper exited with code ${code}`;
  });

  res.status(202).json({ started: true, args: job.args });
});

// GET /api/scraper/run/status
router.get('/run/status', (req, res) => {
  res.json({ ...job, tail: job.tail.slice(-30) });
});

// Identify scraped rows by their address_line (stored as source URL)
const SCRAPED_PATTERN = '%ikman.lk%\' OR p.address_line LIKE \'%house.lk%';

// GET /api/scraper/stats
router.get('/stats', async (req, res) => {
  try {
    const [scraped] = await pool.query(`
      SELECT COUNT(*) AS total,
             SUM(CASE WHEN address_line LIKE '%ikman.lk%' OR address_line LIKE '%house.lk%' THEN 1 ELSE 0 END) AS scraped,
             SUM(CASE WHEN address_line NOT LIKE '%ikman.lk%' AND address_line NOT LIKE '%house.lk%' THEN 1 ELSE 0 END) AS manual
      FROM properties
    `);

    const [byDistrict] = await pool.query(`
      SELECT l.district,
             COUNT(p.id) AS count,
             ROUND(AVG(p.monthly_rent)) AS avg_rent,
             SUM(CASE WHEN p.address_line LIKE '%ikman.lk%' OR p.address_line LIKE '%house.lk%' THEN 1 ELSE 0 END) AS scraped
      FROM properties p
      JOIN locations l ON p.location_id = l.id
      WHERE p.status = 'available'
      GROUP BY l.district
      ORDER BY count DESC
    `);

    const [recent] = await pool.query(`
      SELECT p.id, p.title, p.monthly_rent, p.property_type, p.created_at,
             p.address_line,
             l.district,
             (SELECT url FROM property_images WHERE property_id = p.id ORDER BY is_primary DESC LIMIT 1) AS image
      FROM properties p
      JOIN locations l ON p.location_id = l.id
      ORDER BY p.created_at DESC
      LIMIT 20
    `);

    res.json({
      summary:     scraped[0],
      by_district: byDistrict,
      recent:      recent,
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Server error' });
  }
});

// DELETE /api/scraper/clear-scraped
router.delete('/clear-scraped', async (req, res) => {
  try {
    const [result] = await pool.query(`
      DELETE FROM properties
      WHERE address_line LIKE '%ikman.lk%'
         OR address_line LIKE '%house.lk%'
    `);
    res.json({ deleted: result.affectedRows });
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
