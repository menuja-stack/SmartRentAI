-- ============================================================
-- SmartRentAI - Complete MySQL Database Schema
-- For XAMPP (MySQL 5.7+ / MariaDB 10.3+)
-- Run this in phpMyAdmin or MySQL CLI
-- ============================================================

CREATE DATABASE IF NOT EXISTS smartrentai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smartrentai;

-- ============================================================
-- TABLE 1: USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name     VARCHAR(100)  NOT NULL,
    email         VARCHAR(191)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    role          ENUM('renter','landlord','admin') NOT NULL DEFAULT 'renter',
    avatar_url    VARCHAR(500)  DEFAULT NULL,
    phone         VARCHAR(20)   DEFAULT NULL,
    is_verified   TINYINT(1)   NOT NULL DEFAULT 0,
    verify_token  VARCHAR(255)  DEFAULT NULL,
    reset_token   VARCHAR(255)  DEFAULT NULL,
    reset_expires DATETIME      DEFAULT NULL,
    last_login    DATETIME      DEFAULT NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_role (role),
    INDEX idx_verified (is_verified)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 2: LOCATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS locations (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    city         VARCHAR(100) NOT NULL,
    district     VARCHAR(100) NOT NULL,
    province     VARCHAR(100) NOT NULL,
    postal_code  VARCHAR(20)  DEFAULT NULL,
    latitude     DECIMAL(10,7) DEFAULT NULL,
    longitude    DECIMAL(10,7) DEFAULT NULL,
    INDEX idx_city (city),
    INDEX idx_district (district)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 3: AMENITIES
-- ============================================================
CREATE TABLE IF NOT EXISTS amenities (
    id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    icon VARCHAR(100) DEFAULT NULL
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 4: PROPERTIES
-- ============================================================
CREATE TABLE IF NOT EXISTS properties (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    landlord_id     INT UNSIGNED  NOT NULL,
    location_id     INT UNSIGNED  NOT NULL,
    title           VARCHAR(200)  NOT NULL,
    description     TEXT          NOT NULL,
    property_type   ENUM('apartment','house','room','villa','commercial') NOT NULL,
    status          ENUM('available','rented','inactive') NOT NULL DEFAULT 'available',
    bedrooms        TINYINT UNSIGNED NOT NULL DEFAULT 1,
    bathrooms       TINYINT UNSIGNED NOT NULL DEFAULT 1,
    area_sqft       DECIMAL(8,2)  DEFAULT NULL,
    monthly_rent    DECIMAL(10,2) NOT NULL,
    deposit         DECIMAL(10,2) DEFAULT NULL,
    address_line    VARCHAR(300)  NOT NULL,
    latitude        DECIMAL(10,7) DEFAULT NULL,
    longitude       DECIMAL(10,7) DEFAULT NULL,
    furnished       ENUM('unfurnished','semi-furnished','furnished') DEFAULT 'unfurnished',
    available_from  DATE          DEFAULT NULL,
    views_count     INT UNSIGNED  NOT NULL DEFAULT 0,
    is_featured     TINYINT(1)   NOT NULL DEFAULT 0,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (landlord_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE RESTRICT,
    INDEX idx_landlord (landlord_id),
    INDEX idx_status (status),
    INDEX idx_rent (monthly_rent),
    INDEX idx_type (property_type),
    INDEX idx_bedrooms (bedrooms),
    INDEX idx_coords (latitude, longitude),
    FULLTEXT idx_search (title, description)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 5: PROPERTY IMAGES
-- ============================================================
CREATE TABLE IF NOT EXISTS property_images (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    property_id INT UNSIGNED NOT NULL,
    url         VARCHAR(500) NOT NULL,
    is_primary  TINYINT(1) NOT NULL DEFAULT 0,
    sort_order  TINYINT UNSIGNED NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    INDEX idx_property (property_id)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 6: PROPERTY <-> AMENITIES (pivot)
-- ============================================================
CREATE TABLE IF NOT EXISTS property_amenities (
    property_id INT UNSIGNED NOT NULL,
    amenity_id  INT UNSIGNED NOT NULL,
    PRIMARY KEY (property_id, amenity_id),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    FOREIGN KEY (amenity_id)  REFERENCES amenities(id)  ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 7: SAVED PROPERTIES (wishlist)
-- ============================================================
CREATE TABLE IF NOT EXISTS saved_properties (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NOT NULL,
    property_id INT UNSIGNED NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_property (user_id, property_id),
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 8: USER PREFERENCES
-- ============================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL UNIQUE,
    preferred_city  VARCHAR(100) DEFAULT NULL,
    min_budget      DECIMAL(10,2) DEFAULT NULL,
    max_budget      DECIMAL(10,2) DEFAULT NULL,
    bedrooms        TINYINT UNSIGNED DEFAULT NULL,
    property_type   VARCHAR(50)  DEFAULT NULL,
    furnished_pref  VARCHAR(50)  DEFAULT NULL,
    -- Extended profile (migration 001) — drives "For You" recommendations
    profession          VARCHAR(50)   DEFAULT NULL,
    age_group           VARCHAR(10)   DEFAULT NULL,   -- 18-25, 26-35, 36-45, 46-60, 60+
    family_size         VARCHAR(20)   DEFAULT NULL,   -- Single, Couple, Small Family, Large Family
    has_children        TINYINT(1)    DEFAULT 0,
    has_vehicle         TINYINT(1)    DEFAULT 0,
    current_district    VARCHAR(100)  DEFAULT NULL,
    current_city        VARCHAR(100)  DEFAULT NULL,
    current_rent_budget DECIMAL(10,2) DEFAULT NULL,
    preferred_districts VARCHAR(255)  DEFAULT NULL,   -- CSV, up to 3 districts
    preferred_property_type VARCHAR(50) DEFAULT NULL,
    priority_safety     TINYINT UNSIGNED DEFAULT 3,
    priority_price      TINYINT UNSIGNED DEFAULT 3,
    priority_transport  TINYINT UNSIGNED DEFAULT 3,
    priority_hospital   TINYINT UNSIGNED DEFAULT 3,
    priority_space      TINYINT UNSIGNED DEFAULT 3,
    onboarding_completed TINYINT(1)   DEFAULT 0,
    priorities_learned   TINYINT(1)   DEFAULT 0,      -- set by Phase 7 learning job
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 9: SEARCH HISTORY
-- ============================================================
CREATE TABLE IF NOT EXISTS search_history (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED  DEFAULT NULL,
    query       VARCHAR(500)  NOT NULL,
    filters     JSON          DEFAULT NULL,
    result_count INT UNSIGNED DEFAULT 0,
    property_id INT UNSIGNED  DEFAULT NULL,           -- implicit feedback (Phase 7)
    action      VARCHAR(20)   DEFAULT NULL,           -- view / save / enquiry
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user (user_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 10: RECOMMENDATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS recommendations (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NOT NULL,
    property_id INT UNSIGNED NOT NULL,
    score       DECIMAL(5,4) NOT NULL,
    reason      VARCHAR(300) DEFAULT NULL,
    algo_type   ENUM('collaborative','content','hybrid') DEFAULT 'hybrid',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    INDEX idx_user_score (user_id, score DESC)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 11: RENTAL PRICE PREDICTIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS rental_predictions (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    property_id     INT UNSIGNED  DEFAULT NULL,
    user_id         INT UNSIGNED  DEFAULT NULL,
    input_features  JSON          NOT NULL,
    predicted_price DECIMAL(10,2) NOT NULL,
    confidence      DECIMAL(5,4)  DEFAULT NULL,
    model_version   VARCHAR(20)   DEFAULT '1.0',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 12: CHATBOT SESSIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS chatbot_sessions (
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id    INT UNSIGNED DEFAULT NULL,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at   DATETIME DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_session (session_id)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 13: CHATBOT MESSAGES
-- ============================================================
CREATE TABLE IF NOT EXISTS chatbot_messages (
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    role       ENUM('user','bot') NOT NULL,
    message    TEXT NOT NULL,
    intent     VARCHAR(100) DEFAULT NULL,
    confidence DECIMAL(5,4) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 14: REVIEWS
-- ============================================================
CREATE TABLE IF NOT EXISTS reviews (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    property_id INT UNSIGNED NOT NULL,
    user_id     INT UNSIGNED NOT NULL,
    rating      TINYINT UNSIGNED NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment     TEXT DEFAULT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_property (user_id, property_id),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
    INDEX idx_property (property_id)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 15: ENQUIRIES
-- ============================================================
CREATE TABLE IF NOT EXISTS enquiries (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    property_id INT UNSIGNED NOT NULL,
    renter_id   INT UNSIGNED NOT NULL,
    message     TEXT NOT NULL,
    status      ENUM('pending','replied','closed') NOT NULL DEFAULT 'pending',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    FOREIGN KEY (renter_id)   REFERENCES users(id)      ON DELETE CASCADE,
    INDEX idx_property (property_id),
    INDEX idx_renter (renter_id)
) ENGINE=InnoDB;

-- ============================================================
-- TABLE 16: ANALYTICS LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_logs (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_type  VARCHAR(100) NOT NULL,
    user_id     INT UNSIGNED DEFAULT NULL,
    property_id INT UNSIGNED DEFAULT NULL,
    meta        JSON         DEFAULT NULL,
    ip_address  VARCHAR(45)  DEFAULT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE SET NULL,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL,
    INDEX idx_event (event_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- ============================================================
-- SEED: AMENITIES
-- ============================================================
INSERT IGNORE INTO amenities (name, icon) VALUES
('WiFi','wifi'),('Parking','car'),('Air Conditioning','snowflake'),
('Gym','dumbbell'),('Swimming Pool','water'),('Security','shield'),
('Elevator','arrow-up'),('Generator','zap'),('Water 24/7','droplet'),
('CCTV','camera'),('Garden','tree'),('Laundry','refresh-cw'),
('Pet Friendly','heart'),('Balcony','home'),('Furnished Kitchen','utensils');

-- ============================================================
-- SEED: LOCATIONS (Sri Lanka Districts)
-- ============================================================
INSERT IGNORE INTO locations (city, district, province, latitude, longitude) VALUES
('Colombo','Colombo','Western',6.9271,79.8612),
('Dehiwala','Colombo','Western',6.8516,79.8647),
('Nugegoda','Colombo','Western',6.8708,79.8886),
('Kandy','Kandy','Central',7.2906,80.6337),
('Galle','Galle','Southern',6.0535,80.2210),
('Negombo','Gampaha','Western',7.2094,79.8391),
('Kurunegala','Kurunegala','North Western',7.4867,80.3647),
('Battaramulla','Colombo','Western',6.9000,79.9167),
('Mount Lavinia','Colombo','Western',6.8376,79.8644),
('Sri Jayawardenepura','Colombo','Western',6.8956,79.8985);

-- ============================================================
-- SEED: ADMIN USER (password: Admin@123)
-- bcrypt hash of Admin@123 with 10 rounds
-- ============================================================
INSERT IGNORE INTO users (full_name, email, password_hash, role, is_verified) VALUES
('Admin User', 'admin@smartrentai.lk',
 '$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LsNAjzFcYR2',
 'admin', 1);
