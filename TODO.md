# TODO.md — SmartRentAI Incomplete Work

Last updated: 2026-08-30

---

## ✅ Recently Completed (v1.3.0 — 2026-08-30)

- **Price Prediction retrained on REAL data** — was 2,000 synthetic rows, now 820 real
  scraped/manual rows from the live DB. 3-model comparison (XGBoost, GradientBoosting,
  CatBoost) with Optuna tuning + 5-fold CV; CatBoost wins (CV R²=0.4711, MAE≈LKR 91,679).
  See AI_MODELS.md → Service 2.
- **Fixed a `/predict` 400 crash** (`Feature encoding failed: 'latitude'`) — `train.py`
  now saves district→lat/lng centroids into `encoders.joblib` and `app.py` derives
  lat/lng from the district at serve time, since `/predict` requests never carry raw
  coordinates. A second latent bug (CatBoost needs raw categorical input, not the
  encoded/scaled array the other two models use) was fixed in the same pass —
  `_build_features()` in `app.py` is now model-aware.
- **Model evaluation suite added for all 4 AI services** — non-invasive `evaluate_model.py`
  per service (loads the deployed model, reconstructs the exact held-out test split, never
  retrains or edits the service's own code). Produces confusion matrices, ROC/PR curves,
  predicted-vs-actual, residuals, feature importance, and text reports in each service's
  `outputs/` folder — first defensible evaluation section for Price Prediction,
  Recommendation, and Chatbot (Location Intelligence already had it).
- **Chatbot weakness now empirically measured, not just suspected** — 4-fold stratified
  CV (the deployed model has no held-out set to evaluate against directly) gives
  accuracy 41.5%, F1(macro) 0.34 on the 53-example/10-intent training set. See new HIGH
  priority item below — this replaces the old "no training data docs" LOW item, since
  the docs now exist (AI_MODELS.md) and the real problem is the dataset is too small.

---

## ✅ Recently Completed (v1.2.0 — 2026-07-08)

- **Loading states across every page** — `PageLoader`, `RouteProgress`, `LoadingButton`,
  `AILoader`, and 8 shimmer skeletons. All pages lazy-loaded (per-route code splitting).
  No bare spinners or blank states remain. See CHANGELOG.md.
- **Scraper runs from the admin UI** — `POST /api/scraper/run` + live log console;
  the scraper no longer has to be started from a terminal.
- **Image loading/error states** — shimmer until load, `loading="lazy"`, clean
  "Image unavailable" placeholder instead of broken-image icons.
- **Toasts everywhere** — zero `alert()` / `console.error` left in `frontend/src`.
- **MySQL system-table corruption recovered** — runbook added to CLAUDE.md.

---

## ✅ Completed in v1.1.0 (2026-06-29)

- **Profile-based recommendation system** (7 phases) — replaced the stateless
  recommender with a trained two-stage model (`:8001`), onboarding wizard,
  "For You" page, homepage top-3, and an implicit-feedback learning loop.
  See CHANGELOG.md / AI_MODELS.md.
- **Search history / implicit feedback now recorded** — `POST /api/users/activity`
  logs view/save/enquiry to `search_history` (drives `update_preferences.py`).
- **Recommendation payload bloat fixed** — backend no longer ships ALL properties to
  the AI service per request; `:8001` holds its own cached property matrix.
- **District/town search** — full 25-district dropdown + `GET /api/locations/search`
  autocomplete + URL sync.
- **Scraped location parsing** corrected (URL-first) + **duplicate listings** removed
  (`dedupe_properties.py`) with a title+rent re-listing guard in the scraper.

---

## HIGH Priority

### Reviews & Enquiries — No UI
- `reviews` and `enquiries` tables are fully defined in schema.sql but there are **no API routes or frontend pages** for them
- Users can't leave reviews or contact landlords
- Affects: property detail page, trust/credibility of platform
- **Files to create**: `backend/src/routes/review.routes.js`, `backend/src/routes/enquiry.routes.js`, `backend/src/controllers/review.controller.js`, `backend/src/controllers/enquiry.controller.js`
- **Frontend**: Add review form to `PropertyDetailPage.jsx`, ratings already shown in GET /properties/:id response

### Recommendation results not persisted to `recommendations` table (optional)
- The new profile-based engine (`:8001`) computes "For You" results on demand and
  the backend enriches them live — it does NOT write to the `recommendations` table.
- This is fine functionally; persisting would only help analytics/history.
- Optional fix: INSERT top results into `recommendations` after each `/recommendations` call.

### Chatbot — Training Set Too Small (empirically confirmed)
- 4-fold stratified CV on the 53-example/10-intent dataset gives **accuracy 41.5%,
  F1(macro) 0.34** — see `ai-services/chatbot/outputs/` and AI_MODELS.md → Service 3.
- Root cause: short generic phrases ("thank you", "hello") give TF-IDF very little
  signal with only 4–6 examples per class; several intents share common words.
- **Fix**: either (a) grow `TRAINING_DATA` in `app.py` substantially (aim for 20–30+
  examples per intent), or (b) swap TF-IDF+NB for sentence-transformer embeddings +
  semantic similarity matching, which needs far less data per class to generalise.
  Also add entity extraction (district, budget, bedrooms) so the bot can query the
  `properties` table for real listings instead of only returning templated replies.

### No Email Verification
- `is_verified` is hardcoded to `1` on register (`auth.controller.js` line: `VALUES (?, ?, ?, ?, ?, 1)`)
- `verify_token` is generated but never emailed
- `reset_token` / `reset_expires` exist but no password-reset flow is implemented

---

## MEDIUM Priority

### Search *query* logging (partial)
- `search_history` now records implicit **feedback** (view/save/enquiry via
  `POST /api/users/activity`), but `getProperties()` still does not log the search
  *text/filters* themselves.
- Optional: add `INSERT INTO search_history (query, filters, result_count)` in `getProperties`.

### Analytics — Incomplete Event Logging
- `POST /api/analytics/log` endpoint exists but frontend rarely calls it
- Only `property_view` events are incremented (via `views_count` column)
- `analytics_logs` table is mostly empty
- Fix: add `api.post('/analytics/log', { event_type, ... })` calls in `SearchPage`, `PropertyDetailPage`, `ChatbotPage`

### Chatbot — No Session End Tracking
- `chatbot_sessions.ended_at` is never set
- Sessions accumulate indefinitely
- Fix: call `UPDATE chatbot_sessions SET ended_at = NOW()` on page unload or after inactivity timeout


### LankaPropertyWeb Scraper — Broken
- `ai-services/scraper/scraper.py` skips LankaPropertyWeb — their server returns HTTP 500
- Could be temporary. Add retry logic or check periodically
- See CLAUDE.md → Scraper Selectors

### Property Update — No Image Management
- `PUT /api/properties/:id` cannot add/remove images
- `allowed` fields list in `property.controller.js` does not include image operations
- Landlords can't swap photos after listing

### Pagination — Frontend Search (basic controls exist)
- `SearchPage.jsx` has Previous / "Page N" / Next controls.
- Improvement: use `total_pages` from the API to show numbered pages and disable
  Next on the true last page (currently inferred from `properties.length < 12`).

---

## LOW Priority

### No Avatar Upload
- `users.avatar_url` column exists
- `PUT /api/users/profile` only updates `full_name` and `phone`
- Add Multer endpoint for avatar upload

### Amenities — Not Editable via Admin
- Amenities are seeded in SQL (15 rows) but no admin route to add/edit/delete
- Add `GET/POST/DELETE /api/admin/amenities` if needed for demo

### Scraper — No Scheduling (manual trigger now exists)
- Can be run from the **Admin → Scraper panel** (`POST /api/scraper/run`), but there is
  still no *automatic* schedule.
- Consider: Windows Task Scheduler, node-cron in backend, or cron job
- Also missing: a **Stop/cancel** button for a running job, and a `--no-db` dry-run toggle in the UI

### Property Detail — `getSimilar` Unverified
- `GET /api/recommendations/similar/:id` route exists
- `recommendation.controller.js` `getSimilar` implementation not audited — may return empty/errors

### Missing `.env.example`
- `backend/.env` contains secrets; no `.env.example` for new developers
- Create `backend/.env.example` with placeholder values

### No Production Build Docs
- No documented steps for deploying outside localhost (PM2, Nginx, SSL, environment variables for prod)

---

## Known Issues (bugs not yet fixed)

| Issue | File | Severity |
|-------|------|----------|
| `window.confirm`/`alert` replaced in ScraperPanel — verify no other component still uses them | `frontend/src/components/` | Low |
| `PUT /properties/:id` missing validation (no express-validator unlike POST) | `property.routes.js` | Medium |
| `DELETE /admin/users/:id` has no self-deletion guard (admin could delete own account) | `admin.routes.js` | Medium |
| House.lk may block scraper after repeated requests — no backoff/retry in scraper | `scraper.py` | Low |
| `area_sqft` for scraped properties is NULL (House.lk/Ikman don't always expose it) | scraper.py + DB | Low |
