const { pool } = require('../config/db');
const { validationResult } = require('express-validator');
const path = require('path');

// GET /api/properties  — search + filter
async function getProperties(req, res) {
  try {
    const {
      city, district, type, min_rent, max_rent, bedrooms,
      furnished, search, page = 1, limit = 12, sort = 'created_at'
    } = req.query;

    const offset = (parseInt(page) - 1) * parseInt(limit);
    const params = [];
    let where = 'WHERE p.status = "available"';

    if (city)     { where += ' AND l.city = ?';           params.push(city); }
    if (district) { where += ' AND l.district = ?';       params.push(district); }
    if (type)     { where += ' AND p.property_type = ?';  params.push(type); }
    if (min_rent) { where += ' AND p.monthly_rent >= ?';  params.push(min_rent); }
    if (max_rent) { where += ' AND p.monthly_rent <= ?';  params.push(max_rent); }
    if (bedrooms) { where += ' AND p.bedrooms = ?';       params.push(bedrooms); }
    if (furnished){ where += ' AND p.furnished = ?';      params.push(furnished); }
    if (search)   {
      where += ' AND MATCH(p.title, p.description) AGAINST(? IN BOOLEAN MODE)';
      params.push(`${search}*`);
    }

    const allowedSorts = { created_at: 'p.created_at', rent_asc: 'p.monthly_rent ASC', rent_desc: 'p.monthly_rent DESC' };
    const orderBy = allowedSorts[sort] || 'p.created_at DESC';

    const sql = `
      SELECT p.*, l.city, l.district, l.province, l.latitude as loc_lat, l.longitude as loc_lng,
             u.full_name AS landlord_name,
             (SELECT url FROM property_images WHERE property_id = p.id ORDER BY is_primary DESC, sort_order ASC LIMIT 1) AS primary_image,
             (SELECT AVG(rating) FROM reviews WHERE property_id = p.id) AS avg_rating
      FROM properties p
      JOIN locations l ON p.location_id = l.id
      JOIN users u ON p.landlord_id = u.id
      ${where}
      ORDER BY ${orderBy}
      LIMIT ? OFFSET ?
    `;

    const countSql = `
      SELECT COUNT(*) AS total FROM properties p
      JOIN locations l ON p.location_id = l.id
      ${where}
    `;

    params.push(parseInt(limit), offset);
    const [rows]    = await pool.query(sql, params);
    const [countRows] = await pool.query(countSql, params.slice(0, -2));

    res.json({
      data:        rows,
      total:       countRows[0].total,
      page:        parseInt(page),
      total_pages: Math.ceil(countRows[0].total / parseInt(limit)),
    });
  } catch (err) {
    console.error('getProperties error:', err);
    res.status(500).json({ error: 'Server error' });
  }
}

// GET /api/properties/:id
async function getProperty(req, res) {
  try {
    const [rows] = await pool.query(`
      SELECT p.*, l.city, l.district, l.province,
             u.full_name AS landlord_name, u.email AS landlord_email, u.phone AS landlord_phone,
             (SELECT AVG(rating) FROM reviews WHERE property_id = p.id) AS avg_rating,
             (SELECT COUNT(*) FROM reviews WHERE property_id = p.id) AS review_count
      FROM properties p
      JOIN locations l ON p.location_id = l.id
      JOIN users u ON p.landlord_id = u.id
      WHERE p.id = ?
    `, [req.params.id]);

    if (!rows.length) return res.status(404).json({ error: 'Property not found' });

    const property = rows[0];

    // Load images & amenities
    const [images]   = await pool.query('SELECT * FROM property_images WHERE property_id = ? ORDER BY sort_order', [property.id]);
    const [amenities] = await pool.query(`
      SELECT a.* FROM amenities a
      JOIN property_amenities pa ON a.id = pa.amenity_id
      WHERE pa.property_id = ?
    `, [property.id]);
    const [reviews] = await pool.query(`
      SELECT r.*, u.full_name, u.avatar_url FROM reviews r
      JOIN users u ON r.user_id = u.id
      WHERE r.property_id = ?
      ORDER BY r.created_at DESC LIMIT 5
    `, [property.id]);

    // Log view
    await pool.query('UPDATE properties SET views_count = views_count + 1 WHERE id = ?', [property.id]);

    res.json({ ...property, images, amenities, reviews });
  } catch (err) {
    console.error('getProperty error:', err);
    res.status(500).json({ error: 'Server error' });
  }
}

// POST /api/properties
async function createProperty(req, res) {
  const errors = validationResult(req);
  if (!errors.isEmpty()) return res.status(422).json({ errors: errors.array() });

  const {
    title, description, property_type, bedrooms, bathrooms,
    monthly_rent, address_line, city, district,
  } = req.body;

  // Optional numeric / date fields — convert empty string → null so MySQL
  // doesn't try to coerce '' into a DECIMAL/DATE (which fails with NO_ZERO_DATE).
  const area_sqft      = req.body.area_sqft      || null;
  const deposit        = req.body.deposit        || null;
  const latitude       = req.body.latitude       || null;
  const longitude      = req.body.longitude      || null;
  const available_from = req.body.available_from || null;
  const province       = req.body.province       || 'Unknown';
  const furnished      = req.body.furnished      || 'unfurnished';
  // amenity_ids may arrive as 'amenity_ids[]' (FormData array notation) or 'amenity_ids'
  const raw_amenities  = req.body['amenity_ids[]'] || req.body.amenity_ids || [];
  const amenity_ids    = Array.isArray(raw_amenities) ? raw_amenities : [raw_amenities];

  try {
    // Upsert location
    let [locRows] = await pool.query(
      'SELECT id FROM locations WHERE city = ? AND district = ?', [city, district]
    );
    let locationId;
    if (locRows.length) {
      locationId = locRows[0].id;
    } else {
      const [ins] = await pool.query(
        'INSERT INTO locations (city, district, province) VALUES (?,?,?)',
        [city, district, province || 'Unknown']
      );
      locationId = ins.insertId;
    }

    const [result] = await pool.query(`
      INSERT INTO properties
        (landlord_id, location_id, title, description, property_type, bedrooms, bathrooms,
         area_sqft, monthly_rent, deposit, address_line, latitude, longitude, furnished, available_from)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    `, [
      req.user.id, locationId, title, description, property_type,
      bedrooms, bathrooms, area_sqft, monthly_rent, deposit,
      address_line, latitude, longitude, furnished, available_from
    ]);

    const propertyId = result.insertId;

    // Save amenities
    if (amenity_ids.length) {
      const values = amenity_ids.map(aid => [propertyId, aid]);
      await pool.query('INSERT IGNORE INTO property_amenities (property_id, amenity_id) VALUES ?', [values]);
    }

    // Save uploaded images — store relative path so any host can resolve it
    if (req.files && req.files.length > 0) {
      const imgValues = req.files.map((f, i) => [
        propertyId,
        `/uploads/properties/${f.filename}`,   // served by express.static
        i === 0 ? 1 : 0,
        i,
      ]);
      await pool.query(
        'INSERT INTO property_images (property_id, url, is_primary, sort_order) VALUES ?',
        [imgValues]
      );
    }

    res.status(201).json({ message: 'Property created', id: propertyId });
  } catch (err) {
    console.error('createProperty error:', err);
    res.status(500).json({ error: 'Server error' });
  }
}

// PUT /api/properties/:id
async function updateProperty(req, res) {
  try {
    const [rows] = await pool.query(
      'SELECT landlord_id FROM properties WHERE id = ?', [req.params.id]
    );
    if (!rows.length) return res.status(404).json({ error: 'Property not found' });
    if (rows[0].landlord_id !== req.user.id && req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Access denied' });
    }

    const allowed = ['title','description','monthly_rent','deposit','bedrooms','bathrooms',
                     'area_sqft','furnished','available_from','status','address_line'];
    const fields  = [];
    const values  = [];
    for (const key of allowed) {
      if (req.body[key] !== undefined) { fields.push(`${key} = ?`); values.push(req.body[key]); }
    }
    if (!fields.length) return res.status(400).json({ error: 'No valid fields to update' });

    values.push(req.params.id);
    await pool.query(`UPDATE properties SET ${fields.join(', ')} WHERE id = ?`, values);
    res.json({ message: 'Property updated' });
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
}

// DELETE /api/properties/:id
async function deleteProperty(req, res) {
  try {
    const [rows] = await pool.query('SELECT landlord_id FROM properties WHERE id = ?', [req.params.id]);
    if (!rows.length) return res.status(404).json({ error: 'Property not found' });
    if (rows[0].landlord_id !== req.user.id && req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Access denied' });
    }
    await pool.query('DELETE FROM properties WHERE id = ?', [req.params.id]);
    res.json({ message: 'Property deleted' });
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
}

// POST /api/properties/:id/save
async function toggleSave(req, res) {
  const { id: propertyId } = req.params;
  const userId = req.user.id;
  try {
    const [rows] = await pool.query(
      'SELECT id FROM saved_properties WHERE user_id = ? AND property_id = ?', [userId, propertyId]
    );
    if (rows.length) {
      await pool.query('DELETE FROM saved_properties WHERE user_id = ? AND property_id = ?', [userId, propertyId]);
      res.json({ saved: false });
    } else {
      await pool.query('INSERT INTO saved_properties (user_id, property_id) VALUES (?,?)', [userId, propertyId]);
      res.json({ saved: true });
    }
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
}

// GET /api/properties/saved
async function getSaved(req, res) {
  try {
    const [rows] = await pool.query(`
      SELECT p.*, l.city, l.district,
             (SELECT url FROM property_images WHERE property_id = p.id AND is_primary = 1 LIMIT 1) AS primary_image
      FROM saved_properties sp
      JOIN properties p ON sp.property_id = p.id
      JOIN locations l ON p.location_id = l.id
      WHERE sp.user_id = ?
      ORDER BY sp.created_at DESC
    `, [req.user.id]);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: 'Server error' });
  }
}

module.exports = { getProperties, getProperty, createProperty, updateProperty, deleteProperty, toggleSave, getSaved };
