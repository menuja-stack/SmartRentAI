const multer = require('multer');
const path   = require('path');
const fs     = require('fs');

const storage = multer.diskStorage({
  destination(req, file, cb) {
    const dir = path.join(__dirname, '../../uploads/properties');
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    cb(null, dir);
  },
  filename(req, file, cb) {
    const ext  = path.extname(file.originalname).toLowerCase();
    const name = `prop_${Date.now()}_${Math.random().toString(36).slice(2)}${ext}`;
    cb(null, name);
  },
});

const fileFilter = (req, file, cb) => {
  const allowed = /jpeg|jpg|png|webp/;
  if (allowed.test(path.extname(file.originalname).toLowerCase()) &&
      allowed.test(file.mimetype)) {
    cb(null, true);
  } else {
    cb(new Error('Only JPEG, PNG, and WebP images are allowed'));
  }
};

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: parseInt(process.env.MAX_FILE_SIZE || '5242880') },
});

module.exports = upload;
