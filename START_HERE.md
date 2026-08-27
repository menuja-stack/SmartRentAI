# SmartRentAI — Step-by-Step Startup Guide
**Final Year Project | A.G. Menuja Dulnidu Bandara**

---

## FOLDER STRUCTURE (What was just created)

```
SmartRentAI/
├── backend/                    ← Node.js + Express API (port 5000)
│   ├── src/
│   │   ├── server.js           ← Entry point
│   │   ├── config/db.js        ← MySQL connection (XAMPP)
│   │   ├── controllers/        ← Business logic
│   │   │   ├── auth.controller.js
│   │   │   ├── property.controller.js
│   │   │   ├── recommendation.controller.js
│   │   │   ├── prediction.controller.js
│   │   │   ├── chatbot.controller.js
│   │   │   └── analytics.controller.js
│   │   ├── middleware/
│   │   │   ├── auth.middleware.js   ← JWT verify
│   │   │   └── upload.middleware.js ← Multer images
│   │   └── routes/             ← REST endpoints
│   ├── uploads/                ← Property images stored here
│   ├── package.json
│   └── .env                    ← DB credentials here
│
├── frontend/                   ← React.js app (port 3000)
│   ├── src/
│   │   ├── App.jsx             ← Routes
│   │   ├── index.js
│   │   ├── index.css           ← Tailwind
│   │   ├── api/axios.js        ← HTTP client
│   │   ├── store/              ← Redux
│   │   ├── components/
│   │   │   ├── common/Navbar.jsx
│   │   │   ├── common/Footer.jsx
│   │   │   ├── common/ProtectedRoute.jsx
│   │   │   ├── property/PropertyCard.jsx
│   │   │   ├── property/SafeRentWidget.jsx  ← area safety on detail page
│   │   │   ├── profile/PreferencesWizard.jsx ← 3-step profile form
│   │   │   ├── profile/OnboardingModal.jsx   ← first-login personalization
│   │   │   └── ui/                      ← loaders + skeletons
│   │   │       ├── PageLoader.jsx       ← full-screen loader + route bar
│   │   │       ├── LoadingButton.jsx    ← spinner button
│   │   │       ├── AILoader.jsx         ← AI "thinking" loader
│   │   │       └── skeletons/           ← 8 shimmer placeholders
│   │   └── pages/
│   │       ├── HomePage.jsx
│   │       ├── LoginPage.jsx
│   │       ├── RegisterPage.jsx
│   │       ├── SearchPage.jsx
│   │       ├── PropertyDetailPage.jsx
│   │       ├── RecommendationsPage.jsx
│   │       ├── PredictPricePage.jsx
│   │       ├── ChatbotPage.jsx
│   │       ├── WishlistPage.jsx
│   │       ├── ProfilePage.jsx
│   │       ├── AddPropertyPage.jsx
│   │       └── AdminDashboardPage.jsx
│   └── package.json
│
├── ai-services/
│   ├── recommendation/app.py   ← Hybrid recommender   (port 8001)
│   ├── price-prediction/app.py ← RF + GBR predictor   (port 8002)
│   └── chatbot/app.py          ← NLP intent classifier (port 8003)
│
└── database/schema.sql         ← Complete MySQL schema
```

---

## STEP 1 — Set up the Database (XAMPP)

1. Open **XAMPP Control Panel** → Start **Apache** and **MySQL**
2. Open your browser → go to `http://localhost/phpmyadmin`
3. Click **Import** tab
4. Choose file: `SmartRentAI/database/schema.sql`
5. Click **Go**

✅ This creates the `smartrentai` database with all tables and seed data.

**Admin login credentials (pre-seeded):**
- Email: `admin@smartrentai.lk`
- Password: `Admin@123`

---

## STEP 2 — Start the Backend

Open a terminal in `SmartRentAI/backend/`:

```bash
# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

✅ Backend runs at: `http://localhost:5000`
✅ Test it: `http://localhost:5000/api/health`

**If MySQL password is blank (XAMPP default), `.env` is already set correctly.**
If you set a MySQL password, edit `backend/.env`:
```
DB_PASSWORD=your_password_here
```

---

## STEP 3 — Start the Frontend

Open a NEW terminal in `SmartRentAI/frontend/`:

```bash
# Install dependencies (first time only)
npm install

# Start React development server
npm start
```

✅ Frontend opens at: `http://localhost:3000`

---

## STEP 4 — Start the AI Microservices (Python)

You need **3 separate terminals**, one per service.

### Install Python dependencies (first time only)

```bash
# In ai-services/recommendation/
pip install -r requirements.txt

# In ai-services/price-prediction/
pip install -r requirements.txt

# In ai-services/chatbot/
pip install -r requirements.txt
```

### Start the services

**Terminal A — Recommendation Engine (port 8001):**
```bash
cd ai-services/recommendation
python app.py
```
> First time (or to rebuild the trained model) run the pipeline once before `app.py`:
> ```bash
> python generate_dataset.py          # 10k synthetic training rows
> python build_property_features.py   # needs backend :5000 + location :8004 running
> python train_profile_model.py       # creates profile_model.joblib
> ```
> The model files are git-ignored (~350 MB), so regenerate after a fresh clone.

**Terminal D — Location Intelligence / SafeRent (port 8004):**
```bash
cd ai-services/location-intelligence
python app.py
```
> Required for the SafeRent dashboard, the property-page SafeRent widget, and the
> recommendation feature-build step. First run: `curl -X POST http://localhost:8004/train`.

**Terminal B — Price Prediction (port 8002):**
```bash
cd ai-services/price-prediction
python app.py
```
Then train the model (first time):
```bash
curl -X POST http://localhost:8002/train
```
Or visit `http://localhost:8002/train` in browser (GET not supported — use Postman or curl).

**Terminal C — Chatbot (port 8003):**
```bash
cd ai-services/chatbot
python app.py
```

---

## STEP 5 — Test the Application

| URL | What you see |
|-----|-------------|
| `http://localhost:3000` | Home page |
| `http://localhost:3000/register` | Create account |
| `http://localhost:3000/login` | Login |
| `http://localhost:3000/search` | Browse properties (district + town autocomplete) |
| `http://localhost:3000/recommendations` | **"For You"** profile-based recommendations |
| `http://localhost:3000/safety` | SafeRent district dashboard |
| `http://localhost:3000/predict-price` | AI price prediction |
| `http://localhost:3000/chatbot` | AI chat assistant |
| `http://localhost:3000/admin` | Admin dashboard (admin only) |
| `http://localhost:5000/api/health` | Backend health check |

---

## API Reference (Quick Test with Browser/Postman)

```
GET  /api/properties          → List all properties
GET  /api/properties/:id      → Single property
POST /api/auth/register       → Register user
POST /api/auth/login          → Login → returns JWT token
GET  /api/recommendations     → AI recommendations (requires JWT)
POST /api/predictions/price   → Predict rental price
POST /api/chatbot/message     → Chat with AI bot
GET  /api/analytics/dashboard → Admin dashboard (requires admin JWT)
```

---

## Add Sample Property Data

After logging in as landlord, use the **Add Property** page.
Or seed the database manually:

```sql
USE smartrentai;

-- Insert a sample property (assuming user id=1 and location id=1 exist)
INSERT INTO properties
  (landlord_id, location_id, title, description, property_type,
   bedrooms, bathrooms, monthly_rent, address_line, furnished)
VALUES
  (1, 1, '2BR Apartment in Colombo 7',
   'Beautiful modern apartment with city views, 24/7 security.',
   'apartment', 2, 2, 55000, '45 Park Road, Colombo 7', 'furnished'),
  (1, 4, 'Cozy Room in Kandy',
   'Clean and comfortable room near Kandy lake. WiFi included.',
   'room', 1, 1, 18000, '12 Lake Road, Kandy', 'semi-furnished');
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ECONNREFUSED 3306` | Start MySQL in XAMPP Control Panel |
| **"MySQL shutdown unexpectedly"** in XAMPP | System tables are corrupt after a hard shutdown — follow **CLAUDE.md → MySQL / XAMPP Recovery Runbook** (repair with `aria_chk`, not `myisamchk`) |
| "Run Scraper" button fails to start | Python isn't on the backend's PATH — set `PYTHON_BIN` in `backend/.env` |
| `Cannot GET /api/...` | Make sure backend is running on port 5000 |
| `CORS error` | Check `FRONTEND_URL` in `backend/.env` |
| AI service `Connection refused` | Start the Python microservice first |
| `npm install` fails | Make sure Node.js 18+ is installed |
| `python app.py` fails | Run `pip install -r requirements.txt` first |

---

## What Each Role Can Do

| Feature | Renter | Landlord | Admin |
|---------|--------|----------|-------|
| Browse properties | ✅ | ✅ | ✅ |
| Save to wishlist | ✅ | ✅ | ✅ |
| AI recommendations | ✅ | ✅ | ✅ |
| Price prediction | ✅ | ✅ | ✅ |
| AI chatbot | ✅ | ✅ | ✅ |
| Add/edit listings | ❌ | ✅ | ✅ |
| Admin panel | ❌ | ❌ | ✅ |
| Manage users | ❌ | ❌ | ✅ |
