# SmartRentAI — CLAUDE.md

## Project Identity
- **Name**: SmartRentAI — AI-Powered House Rental Platform for Sri Lanka
- **Student**: A.G. Menuja Dulnidu Bandara
- **ID**: CL/BSCDS/CMU/09/64
- **Institution**: International College of Business and Technology (ICBT)
- **Degree**: BSc in Computer Science (Data Science)
- **Type**: Final Year Project

---

## Architecture Overview

```
Frontend (React :3000)
    ↓ Axios
Backend API (Express :5000)
    ↓ mysql2
MySQL (XAMPP :3306) — database: smartrentai
    ↑
AI Microservices (Python Flask)
    :8001 Recommendation
    :8002 Price Prediction
    :8003 Chatbot
    :8004 Location Intelligence (SafeRent)
```

---

## Tech Stack

### Frontend
- React 18, React Router v6, Redux Toolkit
- Tailwind CSS 3, Framer Motion, Lucide React
- Recharts (charts), Axios (HTTP)
- Pages: HomePage, SearchPage, PropertyDetailPage, AdminDashboardPage,
  ChatbotPage, SafetyDashboardPage, PredictPricePage, RecommendationsPage,
  WishlistPage, ProfilePage, AddPropertyPage, LoginPage, RegisterPage

### Backend
- Node.js + Express.js, JWT auth, bcryptjs
- Multer (image uploads → `backend/uploads/properties/`)
- mysql2/promise, Helmet, express-rate-limit, Morgan
- Port: 5000 | Start: `npm run dev` (nodemon) or `npm start`

### Database
- MySQL via XAMPP (root, no password)
- Database name: `smartrentai`
- 16 tables: users, locations, properties, property_images, amenities,
  property_amenities, saved_properties, user_preferences, search_history,
  recommendations, rental_predictions, chatbot_sessions, chatbot_messages,
  reviews, enquiries, analytics_logs

### AI Microservices (Python Flask)
| Service | Port | File | Status |
|---------|------|------|--------|
| Recommendation | 8001 | `ai-services/recommendation/app.py` | **Trained — profile-based "For You"** |
| Price Prediction | 8002 | `ai-services/price-prediction/app.py` | **Trained on REAL data (CatBoost) — 2026-08-29** |
| Chatbot | 8003 | `ai-services/chatbot/app.py` | Has model (small dataset — see AI_MODELS.md) |
| Location Intelligence | 8004 | `ai-services/location-intelligence/app.py` | Trained |

Every service now has a non-invasive `evaluate_model.py` alongside its `app.py`
(loads the deployed model, reconstructs its real held-out test split, writes report
figures to `outputs/` — never retrains, never edits the service itself). See
AI_MODELS.md for the full metrics from each.

### Web Scraper (Python)
- **Main script**: `ai-services/scraper/scraper.py`
- **Sites**: Ikman.lk + House.lk
- **Downloads images** locally to `backend/uploads/properties/`
- **DB column**: `landlord_id` (NOT `owner_id`) — admin user ID queried dynamically

---

## Current Database State (as of 2026-07-08)
| Table | Rows |
|-------|------|
| users | 6 (admin `mj@gmail.com` id=3) |
| properties | 1,452 scraped/manual |
| locations | 93 |
| property_images | local `/uploads/properties/` |
| user_preferences | 6 (extended with profile + lifestyle columns) |
| search_history | logs implicit feedback (view/save/enquiry) |
| amenities | 15 |

**Admin login**: `mj@gmail.com` — role: admin, id: 3
**Migrations**: `database/migrations/001_extend_user_preferences.sql` (run once; idempotent)

---

## Key File Locations

```
SmartRentAI/
├── CLAUDE.md                              ← this file
├── database/schema.sql                    ← full MySQL schema + seed data
├── backend/
│   ├── .env                               ← DB config, JWT secret, AI service URLs
│   ├── src/server.js                      ← Express app, routes, rate limiting
│   ├── src/config/db.js                   ← mysql2 pool (XAMPP defaults)
│   ├── src/controllers/
│   │   ├── auth.controller.js             ← register, login, getMe, changePassword
│   │   ├── property.controller.js         ← CRUD, search (FULLTEXT), image upload
│   │   └── analytics.controller.js        ← admin dashboard stats
│   ├── src/routes/
│   │   ├── scraper.routes.js              ← /stats, POST /run, /run/status, DELETE /clear-scraped
│   │   ├── locations.routes.js            ← GET /search?q= town/city autocomplete
│   │   └── location.routes.js             ← proxies to :8004 (SafeRent)
│   ├── src/middleware/
│   │   ├── auth.middleware.js             ← JWT authenticate + authorize(role)
│   │   └── upload.middleware.js           ← Multer → uploads/properties/
│   └── uploads/properties/                ← scraped + uploaded property images
├── frontend/
│   ├── src/App.jsx                        ← ALL pages React.lazy + Suspense(PageLoader)
│   ├── src/api/axios.js                   ← Axios instance, 401 → /login redirect
│   ├── src/utils/imageUrl.js              ← getImageUrl() handles /uploads/ + external URLs
│   ├── src/pages/AdminDashboardPage.jsx   ← DashboardSkeleton first load, never blanks on refresh
│   ├── src/components/ui/                 ← loading system (see Loading States below)
│   │   ├── PageLoader.jsx                 ← full-screen loader + RouteProgress bar
│   │   ├── LoadingButton.jsx              ← spinner button, prevents double-submit
│   │   ├── AILoader.jsx                   ← rotating-message loader for AI calls
│   │   └── skeletons/                     ← 8 shimmer skeleton components
│   ├── src/components/profile/
│   │   ├── PreferencesWizard.jsx          ← 3-step profile form (reused by modal)
│   │   └── OnboardingModal.jsx            ← shows once, backend-driven
│   ├── src/components/property/
│   │   ├── PropertyCard.jsx               ← image shimmer + lazy + error placeholder
│   │   └── SafeRentWidget.jsx             ← district SafeRent panel on detail page
│   ├── src/components/dashboard/
│   │   ├── ScraperPanel.jsx               ← stats + Run Scraper form + live log
│   │   └── DatasetUpload.jsx              ← CSV upload → POST :8004/upload-dataset
│   └── src/index.css                      ← box-sizing NOT @apply border-border; .skeleton shimmer
├── database/migrations/                   ← 001_extend_user_preferences.sql
└── ai-services/
    ├── scraper/scraper.py                 ← unified scraper (Ikman + House.lk)
    ├── scraper/dedupe_properties.py       ← one-off duplicate cleanup
    ├── scraper/fix_locations.py           ← one-off district correction
    ├── recommendation/                    ← profile-based "For You" :8001
    │   ├── generate_dataset.py            ← 10k synthetic training rows
    │   ├── build_property_features.py     ← live properties + SafeRent
    │   ├── train_profile_model.py         ← two-stage model training
    │   ├── recommender.py                 ← inference core
    │   ├── update_preferences.py          ← Phase-7 feedback learning job
    │   ├── evaluate_model.py              ← non-invasive eval, reconstructs real test split
    │   └── app.py                         ← Flask service
    ├── location-intelligence/
    │   ├── app.py                         ← SafeRent Score :8004 (train via POST /train)
    │   └── evaluate_model.py              ← non-invasive eval → outputs/fig7_*.png
    ├── chatbot/
    │   ├── app.py                         ← chatbot :8003 (auto-trains on import if no model file)
    │   └── evaluate_model.py              ← 4-fold CV eval (no held-out set in app.py) → outputs/
    └── price-prediction/
        ├── train.py                       ← offline training (real DB data) → price_model.joblib
        ├── evaluate_model.py              ← non-invasive eval → outputs/fig_*.png
        └── app.py                         ← price prediction :8002
```

---

## How to Start Everything

### 1. XAMPP
Start **Apache** + **MySQL** in XAMPP Control Panel

### 2. Backend
```powershell
cd "C:\Users\Menuja\Desktop\Final Year Project\SmartRentAI\backend"
npm run dev
# → http://localhost:5000
```

### 3. Frontend
```powershell
cd "C:\Users\Menuja\Desktop\Final Year Project\SmartRentAI\frontend"
npm start
# → http://localhost:3000
```

### 4. AI Services (start only what you need)
```powershell
cd "C:\Users\Menuja\Desktop\Final Year Project\SmartRentAI\ai-services\location-intelligence"
python app.py   # SafeRent :8004

cd "C:\Users\Menuja\Desktop\Final Year Project\SmartRentAI\ai-services\price-prediction"
python app.py   # Price AI :8002

cd "C:\Users\Menuja\Desktop\Final Year Project\SmartRentAI\ai-services\chatbot"
python app.py   # Chatbot :8003

cd "C:\Users\Menuja\Desktop\Final Year Project\SmartRentAI\ai-services\recommendation"
python app.py   # For You / Recommendations :8001
```

### Recommendation pipeline (regenerate models if needed)
Artifacts are git-ignored (~350 MB). Rebuild in order:
```powershell
cd "C:\Users\Menuja\Desktop\Final Year Project\SmartRentAI\ai-services\recommendation"
python generate_dataset.py          # 10k synthetic rows -> data/profile_property_dataset.csv
python build_property_features.py   # live properties + SafeRent -> data/property_features.csv
python train_profile_model.py       # -> profile_model.joblib + property_features.joblib
python app.py                       # serve :8001
# Phase-7 learning job (on demand / cron):
python update_preferences.py --commit
```

### Price Prediction retrain (on demand — real DB data, no synthetic)
```powershell
cd "C:\Users\Menuja\Desktop\Final Year Project\SmartRentAI\ai-services\price-prediction"
python train.py             # reads properties+locations from MySQL -> price_model.joblib
python app.py                # serve :8002 (restart after retraining)
```

### 5. Web Scraper (run on demand)
> Easiest: **Admin Dashboard → Scraper panel → Run Scraper** (runs it on the server).
> The CLI below does the same thing manually.

```powershell
cd "C:\Users\Menuja\Desktop\Final Year Project\SmartRentAI"

# Scrape Colombo — both sites with images (~4 min)
python ai-services/scraper/scraper.py --pages 2 --district Colombo

# Scrape specific site + district
python ai-services/scraper/scraper.py --site ikman --pages 3 --district Kandy

# Fast — no image downloads
python ai-services/scraper/scraper.py --pages 2 --district Colombo --no-images

# Dry run — no DB write
python ai-services/scraper/scraper.py --pages 1 --no-db
```

---

## Important Facts & Bugs Fixed

### Database Gotchas
- `landlord_id` NOT `owner_id` — properties table column name
- Admin user ID is NOT always 1 — scraper queries `SELECT id FROM users WHERE role='admin'`
- `locations` table has NO `country` column (city, district, province, postal_code, lat, lng only)
- `bedrooms`/`bathrooms` are NOT NULL DEFAULT 1 — scraped rows use `or 0` fallback
- `property_type` ENUM: `'apartment','house','room','villa','commercial'`
- `address_line` stores the **source URL** for scraped properties (used for deduplication)
- `user_preferences` is now a **full profile table** (profession, age, family, budget,
  5 `priority_*` ranks, etc.) — drives the `:8001` recommender. See migration 001.
- `search_history.action` + `property_id` log implicit feedback (view/save/enquiry)

### Recommendation System (Profile-Based "For You")
- Two-stage: Stage 1 RandomForest maps **profile → ideal criteria**; Stage 2 does
  **priority-weighted similarity** against the live property matrix. See AI_MODELS.md.
- Scripts (run in order): `generate_dataset.py` → `build_property_features.py` →
  `train_profile_model.py`; serve with `app.py`. Inference core in `recommender.py`.
- Backend `recommendation.controller.js` builds the profile from `user_preferences`
  and proxies to `:8001`; returns `{ needs_onboarding, recommendations, profile_summary }`.
- Frontend: `RecommendationsPage` ("For You"), `OnboardingModal` (shows once — driven by
  backend `onboarding_completed`, NOT a fragile localStorage flag), homepage top-3.

### Duplicate listings
- Portals (house.lk/ikman) re-post the same listing under a NEW URL, so URL-only
  dedup misses it. `save_property()` also guards on **title + monthly_rent**.
- One-off cleanup: `ai-services/scraper/dedupe_properties.py` (keeps oldest per group).

---

## MySQL / XAMPP Recovery Runbook

**Symptom**: XAMPP shows *"Error: MySQL shutdown unexpectedly"* and Start does nothing.
**Cause (both occurrences)**: MySQL was killed mid-write — force-closing XAMPP, a Windows
restart/shutdown while MySQL ran, or a power cut. This corrupts MariaDB's **Aria-format
system tables** in the `mysql` schema. Project data is InnoDB and recovers itself.

**Always read the log first** — do not guess:
```powershell
Get-Content "C:\xamp\mysql\data\mysql_error.log" -Tail 60
```

| Log message | Fix |
|-------------|-----|
| `Index for table '.\mysql\<t>' is corrupt` / `marked as crashed` | `aria_chk --recover --force "C:/xamp/mysql/data/mysql/<t>"` |
| `doesn't have a correct index definition` (unrepairable) | Restore that table's `.MAD`/`.MAI`/`.frm` from `C:\xamp\mysql\backup\mysql\` |
| `log sequence number … does not match … ib_logfiles` | Usually self-heals; if not, back up + delete `ib_logfile0`/`ib_logfile1` |

Full sweep (repairs every Aria system table):
```bash
cd "C:/xamp/mysql/data"
for f in mysql/*.MAI; do "C:/xamp/mysql/bin/aria_chk.exe" --recover --force --silent "${f%.MAI}"; done
```
Always copy `C:\xamp\mysql\data\mysql` to a timestamped folder before repairing.
`proxies_priv` and `columns_priv` are empty by default — safe to restore from backup.

Test-start outside XAMPP (XAMPP's Start button stays disabled after repeated failures):
```bash
"C:/xamp/mysql/bin/mysqld.exe" --defaults-file="C:/xamp/mysql/bin/my.ini" --standalone &
"C:/xamp/mysql/bin/mysqladmin.exe" -u root ping
"C:/xamp/mysql/bin/mysqladmin.exe" -u root shutdown   # then use the XAMPP panel
```

**Prevention**: always press **Stop** in XAMPP (wait for grey) before closing XAMPP or
shutting down Windows. Back up regularly:
`mysqldump -u root smartrentai > backup.sql`

> Note: `aria_chk` — NOT `myisamchk`. MariaDB system tables are Aria (`.MAD`/`.MAI`),
> not MyISAM (`.MYD`/`.MYI`).

### Image Handling
- Scraped images are downloaded locally — external CDN URLs blocked by hotlinking
- Local path format: `/uploads/properties/uuid.jpg` served by Express static
- `getImageUrl()` in `frontend/src/utils/imageUrl.js` handles all cases + null fallback

### Scraper Selectors
- Ikman cards: `soup.find_all('a', class_=re.compile('gtm-ad-item'))` — tag is `<a>` NOT `<li>`
- Ikman URLs: `/en/ads/{district}/house-rentals` and `/en/ads/{district}/apartment-rentals`
- House.lk URLs: `/rent/house/` and `/rent/apartment/` — cards: `div.property_listing`
- House.lk images use `data-src` (lazy-load) NOT `src`
- LankaPropertyWeb: server returns 500 — currently skipped

### Rate Limiting (server.js)
- Auth routes: 50 req/15min (brute force protection)
- Analytics/admin/scraper routes: **no rate limit** (skip function)
- All other routes: 5000 req/15min
- Old limit was 200/15min → caused 429 errors on admin dashboard

### Frontend
- `index.css`: `box-sizing: border-box` NOT `@apply border-border` (Tailwind build error)
- Axios 401 handler: only redirects to `/login` if not already on an auth page
- AdminDashboardPage: skeleton on FIRST load only — refresh keeps content visible
- ScraperPanel: inline confirm panel + toast notifications (NO `window.confirm`/`alert`)

### Loading States (v1.2.0)
- **All pages are `React.lazy` + `<Suspense fallback={<PageLoader/>}>`** in `App.jsx`.
  This code-splits per route — first visit to a route fetches a small chunk.
- **Never add a bare spinner or `animate-pulse` box.** Use the matching skeleton from
  `components/ui/skeletons/`, or `AILoader` for AI calls (:8001/:8002/:8004).
- Shimmer comes from the `.skeleton` class in `index.css` (has a dark-mode variant).
- Buttons that trigger async work use `<LoadingButton loading loadingText="…">` —
  it auto-disables to prevent double-submit.
- Property images: shimmer until `onLoad`, `loading="lazy"`, and on error render a
  house icon + "Image unavailable" (never a broken-image icon).
- Toasts use the **existing `react-toastify`** (ToastContainer is already mounted in
  `App.jsx`, top-right / 3s). Do NOT add a second toast library.
  There must be **zero `alert()` / `console.error`** calls in `frontend/src`.

---

## Module Status

| Module | Frontend Page | Backend Route | AI Service | Status |
|--------|--------------|---------------|------------|--------|
| Property Search | SearchPage | GET /api/properties | — | ✅ Working |
| Property Detail | PropertyDetailPage | GET /api/properties/:id | — | ✅ Working |
| Add Property | AddPropertyPage | POST /api/properties | — | ✅ Working |
| Auth | LoginPage, RegisterPage | /api/auth/* | — | ✅ Working |
| Admin Dashboard | AdminDashboardPage | /api/analytics/dashboard | — | ✅ Working |
| Web Scraper | ScraperPanel (Admin) | /api/scraper/* | scraper.py | ✅ Working |
| Scraper Runner | ScraperPanel "Run Scraper" | POST /api/scraper/run | scraper.py | ✅ Needs Python on server PATH |
| Wishlist | WishlistPage | /api/properties/saved | — | ✅ Working |
| Profile | ProfilePage | /api/users/* | — | ✅ Working |
| Price AI | PredictPricePage | /api/predictions/* | :8002 | ⚠️ Start AI first |
| Chatbot | ChatbotPage | /api/chatbot/* | :8003 | ⚠️ Start AI first |
| SafeRent Score | SafetyDashboardPage | /api/location/* | :8004 | ⚠️ Start AI first |
| SafeRent widget | PropertyDetailPage (`SafeRentWidget`) | /api/location/score/:district | :8004 | ⚠️ Start AI first |
| For You / Recommendations | RecommendationsPage + OnboardingModal | /api/recommendations/* | :8001 | ✅ Trained — start AI first |
| Town/city search | SearchPage autocomplete | /api/locations/search | — | ✅ Working |
| Dataset Upload | DatasetUpload (Admin) | — | POST :8004/upload-dataset | ⚠️ Start AI first |

---

## Environment Variables (`backend/.env`)
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=           # blank for XAMPP
DB_NAME=smartrentai
JWT_SECRET=smartrentai_super_secret_key_change_in_production_2024
JWT_EXPIRES_IN=7d
FRONTEND_URL=http://localhost:3000
AI_RECOMMENDATION_URL=http://localhost:8001
AI_PRICE_URL=http://localhost:8002
AI_CHATBOT_URL=http://localhost:8003
AI_LOCATION_URL=http://localhost:8004

# Optional — only if `python` is not on the server's PATH (for POST /api/scraper/run)
# PYTHON_BIN=C:\path\to\python.exe
```

---

## SafeRent Score Formula
Weighted composite score 0–100:

| Factor | Weight |
|--------|--------|
| Disaster Risk | 30% |
| Flood Risk | 20% |
| Landslide Risk | 15% |
| Hospital Access | 10% |
| Transport Access | 10% |
| Crime Safety | 10% |
| Rainfall | 5% |

**Dataset**: `C:\Users\Menuja\Desktop\create new data set\data\final\training_dataset.csv`
- 401,775 records, 25 Sri Lankan districts, 1981–present
- Binary label: `disaster_occurred`
- Model: RandomForestClassifier → saved as `location_model.joblib`
