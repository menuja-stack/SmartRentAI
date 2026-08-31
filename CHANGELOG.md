# CHANGELOG.md — SmartRentAI

---

## [1.3.0] — 2026-08-30 — Real-Data Price Model + Model Evaluation Suite

### Headline
Price Prediction (`:8002`) is no longer trained on synthetic data — retrained on 820 real
scraped/manual listings with a proper 3-model comparison. A `/predict` crash introduced by
that retrain was found and fixed the same day. All four AI services now have a standalone,
non-invasive evaluation script that produces report-ready figures (confusion matrices,
ROC/PR curves, predicted-vs-actual, residuals, feature importance) from their real
held-out test data.

---

### Price Prediction — Retrained on Real Data
- `ai-services/price-prediction/train.py` now pulls training data straight from the live
  `properties`/`locations` tables (was: 2,000 rows from `generate_synthetic_data()`).
  1,060 rows fetched → 957 after IQR outlier filtering → 820 used for modelling
  (`area_sqft` dropped, 99.9% null; bedrooms/bathrooms zero-values imputed with district
  median).
- **3-model comparison** (Optuna-tuned, 5-fold CV): XGBoost, GradientBoosting, CatBoost.
  **CatBoost wins on CV R² (0.4711)** — selected by the more robust cross-validated
  metric rather than a single test-split R².
- New artifacts: `price_model.joblib`, `encoders.joblib`, `scaler.joblib` (replacing the
  old synthetic-trained `model.joblib`). The `/train` HTTP endpoint was removed —
  retraining is now `python train.py` (offline, against the live DB) followed by a
  service restart.

### Bug Fix — `/predict` 400 "Feature encoding failed: 'latitude'"
- **Root cause 1**: `train.py`'s data-driven feature selection kept `latitude`/`longitude`
  as model features (43% raw coverage, correlation 0.23–0.28 with price), but
  `encoders.joblib` never stored district→coordinate centroids, and `/predict` requests
  only ever send a district name — never raw coordinates. Fix: `train.py` now saves a
  `district_latlng` + `global_latlng` fallback lookup; `app.py`'s `_build_features()`
  derives lat/lng from the request's district at serve time.
- **Root cause 2 (latent, would have hit next)**: the winning model, CatBoost, needs a
  *raw categorical* DataFrame (native `district`/`property_type` strings via a `Pool`),
  a completely different input schema from XGBoost/GradientBoosting's
  target-encoded-then-scaled array. `_build_features()` is now model-aware and branches
  on `encoders['best_model_name']`.
- Also cleaned up 9 duplicate `python app.py` processes left over from earlier restart
  attempts, all fighting over port 8002.

### Model Evaluation Suite (new — all 4 AI services)
Each service gets a standalone `evaluate_model.py` that loads the **already-trained,
already-deployed** model and reconstructs the **exact** held-out test split used at
training time (same source data, same `random_state`, same split params) — it never
retrains and never modifies the service's own `app.py` or training script. Verified in
every case that reconstructed metrics match the deployed model's saved metrics exactly.

| Service | New outputs |
|---|---|
| Location Intelligence (:8004) | Confusion matrix (counts + normalised), ROC curve, precision-recall curve, feature importance, probability distribution, classification report |
| Price Prediction (:8002) | Model comparison chart, predicted-vs-actual, residual analysis (+ existing correlation heatmap, feature importance) |
| Recommendation (:8001) | Confusion matrices for both Stage-1 classifiers, regression MAE-by-target chart, predicted-vs-actual scatter, feature importance |
| Chatbot (:8003) | Dataset composition, confusion matrix (4-fold CV — see finding below), per-intent F1 |

**Notable finding**: the chatbot has no held-out test set in its production training code
(`app.py` fits on all 53 examples). Evaluated via 4-fold stratified cross-validation
instead — the defensible approach for a dataset this small — and found **accuracy 41.5%,
F1(macro) 0.34**, the weakest of the four services. Documented in AI_MODELS.md and added
to TODO.md as a HIGH-priority item (needs a larger training set or a semantic-embedding
upgrade), rather than left as a silent gap.

See AI_MODELS.md for full metrics per service, and TODO.md for what's still open.

---

## [1.2.0] — 2026-07-08 — Loading States, Scraper UI, DB Recovery

### Headline
Full loading/skeleton system across every page, a one-click scraper runner in the
admin panel, and recovery from a MariaDB system-table corruption.

**Database**: 1,452 properties, 6 users, 93 locations.

---

### Loading States & UI Polish
New reusable components under `frontend/src/components/ui/`:

| Component | Purpose |
|-----------|---------|
| `PageLoader.jsx` | Full-screen loader (breathing house logo, top progress bar, "Finding your perfect home…"). Also exports `RouteProgress` — YouTube-style bar on route change |
| `LoadingButton.jsx` | `<LoadingButton loading loadingText="…">` — spinner + auto-disable, prevents double-submit |
| `AILoader.jsx` | Contextual AI loader: spinning ring + rotating messages (Framer Motion) |
| `skeletons/` | `Skeleton` primitives + PropertyCard, PropertyDetail, Dashboard, Profile, Chat, SafeRent, Recommendation skeletons |

- **Shimmer CSS** added to `index.css` (`.skeleton` class + `@keyframes shimmer`), with a dark-mode variant and a `route-progress` keyframe.
- **Code splitting**: all 13 pages are now `React.lazy` + `<Suspense fallback={<PageLoader/>}>` in `App.jsx` — the single ~260 kB bundle became per-route chunks.
- **Skeletons replace every spinner/blank state**: SearchPage, WishlistPage, HomePage (featured had *no* loading state before), PropertyDetailPage, RecommendationsPage, ProfilePage, AdminDashboardPage, SafetyDashboardPage.
- **AI-context loaders**: PredictPrice ("Analysing property features… / Comparing district prices… / Calculating fair value…" + animated bars), For You ("Reading your preferences… / Scoring available properties… / Ranking your best matches…"), SafeRent ("Analysing disaster records…"). Chatbot already had bouncing-dot typing dots.
- **LoadingButton** wired into Login, Register, Predict Price, Save Profile, PreferencesWizard.
- **Images**: `PropertyCard` shows shimmer behind each image until `onLoad`, uses `loading="lazy"`, and renders a house icon + "Image unavailable" on error (never a broken-image icon).
- **Toasts**: uses the existing `react-toastify` (no new dependency). Wishlist save/remove, recommendation failures, prediction errors, and property-load failures all toast. Zero `alert()` / `console.error` calls remain in `src/`.

### Admin — One-Click Scraper Runner
- `POST /api/scraper/run` spawns the scraper on the server with **validated** args
  (district whitelist, `site ∈ {all,ikman,houselk}`, `pages` clamped 1–5, passed as a
  spawn args array — no shell, no injection). One job at a time (`409` if busy).
- `GET /api/scraper/run/status` returns job state + last 30 log lines.
- `ScraperPanel.jsx`: the static command list became a form (Site / District / Pages /
  No-images) with a **Run Scraper** button, live log console, "✓ Saved N · skipped M"
  summary, and progress that resumes if you navigate away.
- Requires Python on the server PATH; override with `PYTHON_BIN` in `backend/.env`.

### Database Recovery (MariaDB system tables)
A hard shutdown corrupted the Aria-format **privilege tables** in the `mysql` schema
(`proxies_priv` index destroyed, `db` / `tables_priv` corrupt, ~20 more not-closed-properly),
which made mysqld abort on startup. Project data (InnoDB) was never at risk.
Fixed by: safety-copying the schema, `aria_chk --recover --force` on all Aria tables, and
restoring `proxies_priv` + `columns_priv` from `C:\xamp\mysql\backup\`.
See CLAUDE.md → **MySQL / XAMPP Recovery** for the full runbook.

---

## [1.1.0] — 2026-06-29 — Profile-Based Recommendations + Data Quality

### Headline
Replaced the stateless recommender with a **trained, profile-based "For You" engine**
and shipped a set of data-quality and search/UX fixes.

**Database**: ~995 properties, 6 users, 83 locations. `user_preferences` extended
with 18 onboarding/lifestyle columns; `search_history` extended for implicit feedback.

---

### Profile-Based Recommendation System (7 phases)
A two-stage hybrid recommender driven by the user's lifestyle profile.

- **Phase 1 — Profile schema + onboarding form**
  - Migration `database/migrations/001_extend_user_preferences.sql` adds profession,
    age_group, family_size, has_children, has_vehicle, current_district/city,
    current_rent_budget, preferred_districts (CSV), preferred_property_type,
    5× `priority_*` (1–5), `onboarding_completed`, `priorities_learned`.
  - `frontend/src/components/profile/PreferencesWizard.jsx` — reusable 3-step form
    (Basic info → Rental needs → priority sliders). Used by ProfilePage **and** the
    post-register `OnboardingModal.jsx`.
  - Backend `PUT /api/users/preferences` rewritten to whitelist-upsert all new fields.
- **Phase 2 — Synthetic dataset** — `ai-services/recommendation/generate_dataset.py`
  → `data/profile_property_dataset.csv` (10,000 rows, profile → ideal criteria;
  encodes SL rental domain rules).
- **Phase 3 — Real data enrichment** — `build_property_features.py`
  → `data/property_features.csv` (live properties joined to SafeRent scores).
- **Phase 4 — Training** — `train_profile_model.py`.
  Stage 1 (profile → criteria): per-target RandomForest, **F1 0.69–0.81**,
  **MAE 2.3–2.6** (beats XGBoost on 4/5 continuous targets).
  Stage 2 (criteria → property): priority-weighted satisfaction matching.
  Artifacts: `profile_model.joblib`, `property_features.joblib`.
- **Phase 5 — API (:8001)** — rewrote `app.py` + new `recommender.py`.
  `POST /recommend` (match_score + match_reasons + profile_summary),
  `GET /recommend/profile-insights/:user_id`. Cold-start defaults by profession.
- **Phase 6 — Frontend** — "For You" `RecommendationsPage.jsx` (match-% badges,
  "Why this?"), homepage top-3, one-time `OnboardingModal`.
- **Phase 7 — Implicit feedback loop** — `POST /api/users/activity` logs view/save/
  enquiry to `search_history`; `update_preferences.py` re-weights `priority_*` from
  behaviour (view=1, save=3, enquiry=5).

### Search & Location UX
- `SearchPage.jsx`: full 25-district dropdown grouped by province (`<optgroup>`);
  town/area autocomplete via new `GET /api/locations/search`; "Showing results in"
  chip; URL sync (`?district=&city=`).
- SafeRent widget (`SafeRentWidget.jsx`) embedded on PropertyDetailPage; deep-links
  to the SafeRent dashboard pre-filtered by district.

### Data Quality
- **Location parsing fix** (`scraper.py`): district resolved from the listing URL
  (`-for-rent-{district}`) → title → page slug, never the sidebar. One-off
  `fix_locations.py` corrected 229 mislabelled rows.
- **Duplicate listings fix**: portals re-post the same listing under a new URL.
  Added a title+rent re-listing guard in `save_property()`; one-off
  `dedupe_properties.py` removed 45 duplicate rows (41 groups).

---

## [1.0.0] — 2026-06-20 — Initial Working Build

### Project State
First stable version of SmartRentAI as submitted for Final Year Project review.

**Database**: 743 properties, 742 local images, 3 users, 55 locations, 36 predictions, 52 chatbot messages.

---

### Features Implemented

**Authentication**
- Register / Login with JWT (7-day expiry)
- Role-based access: renter, landlord, admin
- Change password endpoint
- Auto-verify on register (email verification scaffolded but not wired)

**Property Listings**
- Full CRUD for properties (landlord/admin only for create/edit/delete)
- FULLTEXT search on title + description
- Filter by city, district, type, rent range, bedrooms, furnished status
- Pagination (default 12 per page)
- Image upload via Multer (up to 10 images, served from `/uploads/properties/`)
- Wishlist (save/unsave toggle per user)
- View counter per property

**Admin Dashboard**
- Analytics: total users, properties, predictions, chats; role breakdown; top cities; rent trends
- User management: list, change role, delete
- Property management: list all, change status
- Scraper panel: live stats, recent listings with source badges, one-click clear

**Web Scraper** (`ai-services/scraper/scraper.py`)
- Scrapes Ikman.lk (house + apartment rentals) and House.lk
- Downloads images locally — avoids CDN hotlink blocking
- Deduplicates via `address_line` (source URL)
- Flags: `--pages N`, `--district X`, `--site ikman|house`, `--no-images`, `--no-db`
- 742 properties scraped as of this date

**AI Services**
- **Recommendation** (:8001): hybrid content-based + collaborative filtering, stateless
- **Price Prediction** (:8002): RF + GBR ensemble, trained on synthetic Sri Lankan data
- **Chatbot** (:8003): intent-based classifier, offline, session-aware
- **Location Intelligence** (:8004): RandomForestClassifier trained on 401,775 records; SafeRent Score 0–100; supports live weather input and district comparison

**Frontend Pages**
- HomePage, SearchPage, PropertyDetailPage, AddPropertyPage
- LoginPage, RegisterPage, ProfilePage
- AdminDashboardPage (with ScraperPanel + DatasetUpload)
- ChatbotPage, SafetyDashboardPage, PredictPricePage
- RecommendationsPage, WishlistPage

---

### Fixes Applied in This Build

| Fix | Detail |
|-----|--------|
| Ikman scraper selector | Changed `find_all('li')` → `find_all('a', class_=re.compile('gtm-ad-item'))` |
| DB column name | `owner_id` → `landlord_id` in scraper INSERT |
| Admin user ID | Dynamic query instead of hardcoded `id=1` |
| Scraped images | Downloaded locally; external CDN URLs hotlink-blocked |
| Rate limiting | Raised from 200 to 5000/15min; admin/analytics/scraper exempt |
| Admin dashboard refresh | Separate `refreshing` state — page no longer blanks on Refresh click |
| Confirm/alert dialogs | Replaced `window.confirm`/`window.alert` with inline React UI |
| Axios 401 redirect | Guard against redirect loop on auth pages |
| Port 5000 conflict | Document: use `npx kill-port 5000` if server fails to start |
| `bedrooms` NOT NULL | Scraped rows use `prop.get('bedrooms') or 0` fallback |
| `locations` schema | Removed `country` column from scraper INSERT |

---

### Known Gaps (see TODO.md)
- No reviews or enquiries UI
- No email verification / password reset
- Search history not recorded
- Recommendation results not persisted to DB
- Price model trained on synthetic data only
