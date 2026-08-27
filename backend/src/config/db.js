const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host:               process.env.DB_HOST     || 'localhost',
  port:               parseInt(process.env.DB_PORT || '3306'),
  user:               process.env.DB_USER     || 'root',
  password:           process.env.DB_PASSWORD || '',
  database:           process.env.DB_NAME     || 'smartrentai',
  waitForConnections: true,
  connectionLimit:    10,
  queueLimit:         0,
  timezone:           '+00:00',
  charset:            'utf8mb4',
  // Reconnect automatically if MySQL restarts (e.g. XAMPP restart)
  enableKeepAlive:    true,
  keepAliveInitialDelay: 10000,
});

async function testConnection(retries = 5, delayMs = 3000) {
  for (let i = 1; i <= retries; i++) {
    try {
      const conn = await pool.getConnection();
      console.log('✅ MySQL connected successfully');
      conn.release();
      return;
    } catch (err) {
      console.error(`❌ MySQL connection failed (attempt ${i}/${retries}): ${err.message}`);
      if (i === retries) {
        console.error('   Start XAMPP MySQL and save any file to trigger nodemon restart.');
        process.exit(1);
      }
      await new Promise(r => setTimeout(r, delayMs));
    }
  }
}

module.exports = { pool, testConnection };
