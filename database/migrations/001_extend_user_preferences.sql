-- ============================================================
-- Migration 001 — Extend user_preferences for profile-based
-- personalized recommendations ("For You" feature).
-- Idempotent: uses ADD COLUMN IF NOT EXISTS (MariaDB 10.4+).
-- ============================================================

-- ── Personal ────────────────────────────────────────────────
ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS profession        VARCHAR(50)   DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS age_group         VARCHAR(10)   DEFAULT NULL,   -- 18-25, 26-35, 36-45, 46-60, 60+
  ADD COLUMN IF NOT EXISTS family_size       VARCHAR(20)   DEFAULT NULL,   -- Single, Couple, Small Family, Large Family
  ADD COLUMN IF NOT EXISTS has_children      TINYINT(1)    DEFAULT 0,
  ADD COLUMN IF NOT EXISTS has_vehicle       TINYINT(1)    DEFAULT 0;

-- ── Current situation ───────────────────────────────────────
ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS current_district     VARCHAR(100)  DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS current_city         VARCHAR(100)  DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS current_rent_budget  DECIMAL(10,2) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS preferred_districts  VARCHAR(255)  DEFAULT NULL,  -- CSV, up to 3 districts
  ADD COLUMN IF NOT EXISTS preferred_property_type VARCHAR(50) DEFAULT NULL; -- apartment/house/room/villa

-- ── Lifestyle priorities (rank 1-5 each) ────────────────────
ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS priority_safety    TINYINT UNSIGNED DEFAULT 3,
  ADD COLUMN IF NOT EXISTS priority_price     TINYINT UNSIGNED DEFAULT 3,
  ADD COLUMN IF NOT EXISTS priority_transport TINYINT UNSIGNED DEFAULT 3,
  ADD COLUMN IF NOT EXISTS priority_hospital  TINYINT UNSIGNED DEFAULT 3,
  ADD COLUMN IF NOT EXISTS priority_space     TINYINT UNSIGNED DEFAULT 3;

-- ── Onboarding / learning bookkeeping ───────────────────────
ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS onboarding_completed TINYINT(1) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS priorities_learned   TINYINT(1) DEFAULT 0;  -- set by Phase 7 job

-- ── search_history: add action column for implicit feedback (Phase 7) ──
ALTER TABLE search_history
  ADD COLUMN IF NOT EXISTS property_id INT UNSIGNED DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS action      VARCHAR(20)  DEFAULT NULL;  -- view / save / enquiry
