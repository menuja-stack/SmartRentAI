# SCHEMA.md — SmartRentAI Database Schema

Database: `smartrentai` (MySQL via XAMPP, utf8mb4)
Full DDL: `database/schema.sql`

---

## Table 1: `users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | auto_increment |
| `full_name` | VARCHAR(100) | NOT NULL |
| `email` | VARCHAR(191) | UNIQUE NOT NULL |
| `password_hash` | VARCHAR(255) | bcrypt 10 rounds |
| `role` | ENUM | `renter` \| `landlord` \| `admin` |
| `avatar_url` | VARCHAR(500) | nullable |
| `phone` | VARCHAR(20) | nullable |
| `is_verified` | TINYINT(1) | default 0; currently auto-set to 1 on register |
| `verify_token` | VARCHAR(255) | nullable |
| `reset_token` | VARCHAR(255) | nullable |
| `reset_expires` | DATETIME | nullable |
| `last_login` | DATETIME | updated on each login |
| `created_at` | DATETIME | auto |
| `updated_at` | DATETIME | auto update |

**Indexes**: `role`, `is_verified`
**Current rows**: 6 (admin `mj@gmail.com` id=3)

---

## Table 2: `locations`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `city` | VARCHAR(100) | NOT NULL |
| `district` | VARCHAR(100) | NOT NULL |
| `province` | VARCHAR(100) | NOT NULL |
| `postal_code` | VARCHAR(20) | nullable |
| `latitude` | DECIMAL(10,7) | nullable |
| `longitude` | DECIMAL(10,7) | nullable |

**Indexes**: `city`, `district`
**No `country` column** — do not add to INSERT statements
**Current rows**: 93

---

## Table 3: `amenities`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `name` | VARCHAR(100) | UNIQUE |
| `icon` | VARCHAR(100) | Lucide icon name |

**Seeded**: 15 amenities (WiFi, Parking, AC, Gym, Pool, Security, Elevator, Generator, Water 24/7, CCTV, Garden, Laundry, Pet Friendly, Balcony, Furnished Kitchen)

---

## Table 4: `properties`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `landlord_id` | INT UNSIGNED FK→users | ON DELETE CASCADE |
| `location_id` | INT UNSIGNED FK→locations | ON DELETE RESTRICT |
| `title` | VARCHAR(200) | NOT NULL |
| `description` | TEXT | NOT NULL |
| `property_type` | ENUM | `apartment\|house\|room\|villa\|commercial` |
| `status` | ENUM | `available\|rented\|inactive` default available |
| `bedrooms` | TINYINT UNSIGNED | NOT NULL default 1 — use `or 0` for scraped data |
| `bathrooms` | TINYINT UNSIGNED | NOT NULL default 1 |
| `area_sqft` | DECIMAL(8,2) | nullable |
| `monthly_rent` | DECIMAL(10,2) | NOT NULL |
| `deposit` | DECIMAL(10,2) | nullable |
| `address_line` | VARCHAR(300) | **stores source URL for scraped rows** |
| `latitude` | DECIMAL(10,7) | nullable |
| `longitude` | DECIMAL(10,7) | nullable |
| `furnished` | ENUM | `unfurnished\|semi-furnished\|furnished` |
| `available_from` | DATE | nullable |
| `views_count` | INT UNSIGNED | auto-incremented on GET /properties/:id |
| `is_featured` | TINYINT(1) | default 0 |
| `created_at` | DATETIME | auto |
| `updated_at` | DATETIME | auto update |

**FULLTEXT index** on `(title, description)` — used by `MATCH ... AGAINST(? IN BOOLEAN MODE)`
**Deduplication**: before insert, check `address_line` for existing source URL
**Current rows**: 1,452 (mostly scraped)
**Dedup**: unique on source URL (`address_line`) AND on `title` + `monthly_rent`
(portals re-post the same listing under a new URL). See `scraper/dedupe_properties.py`.

---

## Table 5: `property_images`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `property_id` | INT UNSIGNED FK→properties | ON DELETE CASCADE |
| `url` | VARCHAR(500) | `/uploads/properties/filename.jpg` (relative) |
| `is_primary` | TINYINT(1) | 1 = main display image |
| `sort_order` | TINYINT UNSIGNED | display order |
| `created_at` | DATETIME | |

**Current rows**: one primary image per scraped property (all stored locally)

---

## Table 6: `property_amenities` (pivot)

| Column | Type | Notes |
|--------|------|-------|
| `property_id` | INT UNSIGNED FK→properties | composite PK |
| `amenity_id` | INT UNSIGNED FK→amenities | composite PK |

---

## Table 7: `saved_properties`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `user_id` | INT UNSIGNED FK→users | ON DELETE CASCADE |
| `property_id` | INT UNSIGNED FK→properties | ON DELETE CASCADE |
| `created_at` | DATETIME | |

**UNIQUE**: `(user_id, property_id)` — toggle via INSERT / DELETE

---

## Table 8: `user_preferences`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `user_id` | INT UNSIGNED FK→users | UNIQUE (1 row per user) |
| `preferred_city` | VARCHAR(100) | legacy, nullable |
| `min_budget` | DECIMAL(10,2) | legacy, nullable |
| `max_budget` | DECIMAL(10,2) | legacy, nullable |
| `bedrooms` | TINYINT UNSIGNED | legacy, nullable |
| `property_type` | VARCHAR(50) | legacy, nullable |
| `furnished_pref` | VARCHAR(50) | legacy, nullable |
| **Profile** (migration 001) | | |
| `profession` | VARCHAR(50) | Doctor, Engineer, Student, … |
| `age_group` | VARCHAR(10) | 18-25, 26-35, 36-45, 46-60, 60+ |
| `family_size` | VARCHAR(20) | Single, Couple, Small Family, Large Family |
| `has_children` | TINYINT(1) | 0/1 |
| `has_vehicle` | TINYINT(1) | 0/1 |
| `current_district` | VARCHAR(100) | nullable |
| `current_city` | VARCHAR(100) | nullable |
| `current_rent_budget` | DECIMAL(10,2) | monthly max (LKR) |
| `preferred_districts` | VARCHAR(255) | CSV, up to 3 districts |
| `preferred_property_type` | VARCHAR(50) | apartment/house/room/villa |
| `priority_safety` | TINYINT UNSIGNED | 1–5 (default 3) |
| `priority_price` | TINYINT UNSIGNED | 1–5 (default 3) |
| `priority_transport` | TINYINT UNSIGNED | 1–5 (default 3) |
| `priority_hospital` | TINYINT UNSIGNED | 1–5 (default 3) |
| `priority_space` | TINYINT UNSIGNED | 1–5 (default 3) |
| `onboarding_completed` | TINYINT(1) | drives the onboarding modal |
| `priorities_learned` | TINYINT(1) | set by the Phase-7 learning job |
| `updated_at` | DATETIME | auto update |

**Upsert**: `INSERT ... ON DUPLICATE KEY UPDATE` (whitelist; partial saves supported)
**Drives**: the profile-based recommender (`:8001`). See AI_MODELS.md → Service 1.

---

## Table 9: `search_history`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `user_id` | INT UNSIGNED FK→users | nullable (anonymous) |
| `query` | VARCHAR(500) | search text / `action:property_id` |
| `filters` | JSON | filter params |
| `result_count` | INT UNSIGNED | |
| `property_id` | INT UNSIGNED | implicit feedback target (migration 001) |
| `action` | VARCHAR(20) | view / save / enquiry (migration 001) |
| `created_at` | DATETIME | |

**Used by**: the Phase-7 feedback loop (`update_preferences.py`) to re-weight priorities.

---

## Table 10: `recommendations`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `user_id` | INT UNSIGNED FK→users | |
| `property_id` | INT UNSIGNED FK→properties | |
| `score` | DECIMAL(5,4) | 0.0000 – 1.0000 |
| `reason` | VARCHAR(300) | human-readable explanation |
| `algo_type` | ENUM | `collaborative\|content\|hybrid` |
| `created_at` | DATETIME | |

---

## Table 11: `rental_predictions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `property_id` | INT UNSIGNED FK→properties | nullable |
| `user_id` | INT UNSIGNED FK→users | nullable |
| `input_features` | JSON | district, bedrooms, etc. |
| `predicted_price` | DECIMAL(10,2) | |
| `confidence` | DECIMAL(5,4) | nullable |
| `model_version` | VARCHAR(20) | default '1.0' |
| `created_at` | DATETIME | |

**Current rows**: 36

---

## Table 12: `chatbot_sessions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `user_id` | INT UNSIGNED FK→users | nullable |
| `session_id` | VARCHAR(100) | UNIQUE — UUID from frontend |
| `started_at` | DATETIME | |
| `ended_at` | DATETIME | nullable |

**Current rows**: 5

---

## Table 13: `chatbot_messages`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `session_id` | VARCHAR(100) | FK-like (no constraint) |
| `role` | ENUM | `user\|bot` |
| `message` | TEXT | |
| `intent` | VARCHAR(100) | nullable — from AI classifier |
| `confidence` | DECIMAL(5,4) | nullable |
| `created_at` | DATETIME | |

**Current rows**: 52

---

## Table 14: `reviews`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `property_id` | INT UNSIGNED FK→properties | |
| `user_id` | INT UNSIGNED FK→users | |
| `rating` | TINYINT UNSIGNED | CHECK 1–5 |
| `comment` | TEXT | nullable |
| `created_at` | DATETIME | |

**UNIQUE**: `(user_id, property_id)` — one review per user per property

---

## Table 15: `enquiries`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `property_id` | INT UNSIGNED FK→properties | |
| `renter_id` | INT UNSIGNED FK→users | |
| `message` | TEXT | NOT NULL |
| `status` | ENUM | `pending\|replied\|closed` |
| `created_at` | DATETIME | |

---

## Table 16: `analytics_logs`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT UNSIGNED PK | |
| `event_type` | VARCHAR(100) | e.g. `property_view`, `search` |
| `user_id` | INT UNSIGNED FK→users | nullable (anonymous events) |
| `property_id` | INT UNSIGNED FK→properties | nullable |
| `meta` | JSON | arbitrary payload |
| `ip_address` | VARCHAR(45) | supports IPv6 |
| `created_at` | DATETIME | |

---

## Key Relationships

```
users ──< properties (landlord_id)
users ──< saved_properties ──> properties
users ──< user_preferences
users ──< reviews ──> properties
users ──< enquiries ──> properties
users ──< recommendations ──> properties
users ──< rental_predictions
users ──< chatbot_sessions
locations ──< properties
properties ──< property_images
properties ──< property_amenities ──> amenities
```
