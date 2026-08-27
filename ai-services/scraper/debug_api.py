"""Debug: check what the DB subquery actually returns for primary_image"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import mysql.connector

conn = mysql.connector.connect(
    host='localhost', port=3306, user='root', password='',
    database='smartrentai', charset='utf8mb4',
)
cur = conn.cursor(dictionary=True)

# 1. Show property_images rows directly
print('=== property_images rows (latest 5) ===')
cur.execute("""
    SELECT pi.id, pi.property_id, pi.url, pi.is_primary
    FROM property_images pi
    ORDER BY pi.id DESC LIMIT 5
""")
for r in cur.fetchall():
    print(f"  pi.id={r['id']}  property_id={r['property_id']}  is_primary={r['is_primary']}  url={r['url']}")

# 2. Run the EXACT same subquery the Express backend uses
print()
print('=== EXACT getProperties subquery result (first 5 properties) ===')
cur.execute("""
    SELECT p.id, p.title,
           (SELECT url FROM property_images WHERE property_id = p.id
            ORDER BY is_primary DESC, sort_order ASC LIMIT 1) AS primary_image
    FROM properties p
    ORDER BY p.created_at DESC
    LIMIT 5
""")
for r in cur.fetchall():
    print(f"  p.id={r['id']}  primary_image={r['primary_image']!r}  title={r['title'][:50]}")

# 3. Check for any property_id mismatches (orphaned images or unmatched)
print()
print('=== Orphaned property_images (property_id not in properties) ===')
cur.execute("""
    SELECT COUNT(*) AS orphaned
    FROM property_images pi
    LEFT JOIN properties p ON pi.property_id = p.id
    WHERE p.id IS NULL
""")
print(f"  orphaned: {cur.fetchone()['orphaned']}")

print()
print('=== Properties with NO image ===')
cur.execute("""
    SELECT COUNT(*) AS no_img
    FROM properties p
    WHERE NOT EXISTS (SELECT 1 FROM property_images WHERE property_id = p.id)
""")
print(f"  properties with no image: {cur.fetchone()['no_img']}")

print()
print('=== Count of property_images rows ===')
cur.execute("SELECT COUNT(*) AS cnt FROM property_images")
print(f"  total rows: {cur.fetchone()['cnt']}")

cur.close()
conn.close()
