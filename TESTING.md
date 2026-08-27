# TESTING.md — SmartRentAI Test Reference

Base URL: `http://localhost:5000/api`
Run backend first: see CLAUDE.md → How to Start Everything

---

## Test Accounts

| Role | Email | Password | User ID |
|------|-------|----------|---------|
| Admin | `mj@gmail.com` | _(your password)_ | 3 |
| Seed admin | `admin@smartrentai.lk` | `Admin@123` | 1 (if seed was run) |

> **Get a token**: run the login curl below and copy the `token` value. Use as `Bearer <token>` in subsequent requests.

---

## Auth Endpoints

### Register
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Renter",
    "email": "test@example.com",
    "password": "password123",
    "role": "renter"
  }'
```

### Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "mj@gmail.com", "password": "YOUR_PASSWORD"}'
```
**Save token**: `TOKEN=$(curl -s ... | jq -r '.token')`

### Get Current User
```bash
curl http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Change Password
```bash
curl -X PUT http://localhost:5000/api/auth/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_password": "old123", "new_password": "new123456"}'
```

---

## Property Endpoints

### Search Properties (no auth)
```bash
# All available
curl "http://localhost:5000/api/properties"

# With filters
curl "http://localhost:5000/api/properties?district=Colombo&type=house&min_rent=30000&max_rent=150000&page=1&limit=5"

# Full text search
curl "http://localhost:5000/api/properties?search=garden+room+Kandy"

# Sort by rent ascending
curl "http://localhost:5000/api/properties?sort=rent_asc&limit=10"
```

### Get Single Property
```bash
curl "http://localhost:5000/api/properties/1"
```
Expected: `{ id, title, images: [...], amenities: [...], reviews: [...], ... }`

### Create Property (landlord/admin)
```bash
curl -X POST http://localhost:5000/api/properties \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Spacious 2BR Apartment in Colombo 7" \
  -F "description=Modern apartment with great city views and easy highway access." \
  -F "property_type=apartment" \
  -F "bedrooms=2" \
  -F "bathrooms=1" \
  -F "monthly_rent=85000" \
  -F "address_line=45 Independence Ave, Colombo 7" \
  -F "city=Colombo" \
  -F "district=Colombo" \
  -F "furnished=furnished" \
  -F "images=@/path/to/photo.jpg"
```

### Toggle Wishlist
```bash
curl -X POST http://localhost:5000/api/properties/5/save \
  -H "Authorization: Bearer $TOKEN"
# {"saved": true} or {"saved": false}
```

### Get Saved Properties
```bash
curl http://localhost:5000/api/properties/saved \
  -H "Authorization: Bearer $TOKEN"
```

---

## Price Prediction

> Start `:8002` first: `cd ai-services/price-prediction && python app.py`

```bash
curl -X POST http://localhost:5000/api/predictions/price \
  -H "Content-Type: application/json" \
  -d '{
    "district": "Colombo",
    "property_type": "apartment",
    "bedrooms": 2,
    "bathrooms": 1,
    "area_sqft": 850,
    "furnished": "furnished",
    "has_parking": 1,
    "has_pool": 0,
    "has_gym": 0
  }'
```

```bash
# Direct to AI service (bypasses backend)
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -d '{"district":"Kandy","property_type":"house","bedrooms":3,"bathrooms":2,"area_sqft":1200,"furnished":"semi-furnished","has_parking":1,"has_pool":0,"has_gym":0}'
```

### Train on synthetic data
```bash
curl -X POST http://localhost:8002/train
```

---

## Chatbot

> Start `:8003` first: `cd ai-services/chatbot && python app.py`

```bash
curl -X POST http://localhost:5000/api/chatbot/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me houses for rent in Colombo under 80000",
    "session_id": "test-session-001",
    "user_id": 3
  }'
```

### Get Chat History (auth required)
```bash
curl "http://localhost:5000/api/chatbot/history/test-session-001" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Recommendations (Profile-Based "For You")

> Start `:8001` first: `cd ai-services/recommendation && python app.py`
> (and `:8004` location service, which the feature-build step uses)

```bash
# "For You" for the logged-in user (built from their saved profile)
curl http://localhost:5000/api/recommendations \
  -H "Authorization: Bearer $TOKEN"
#   -> { needs_onboarding, recommendations:[{ match_score, match_reasons, ... }], profile_summary }

# What the model inferred about this user
curl http://localhost:5000/api/recommendations/insights \
  -H "Authorization: Bearer $TOKEN"

# Similar properties (no auth)
curl http://localhost:5000/api/recommendations/similar/5

# Direct to the AI service (bypass backend): raw profile -> recommendations
curl -X POST http://localhost:8001/recommend \
  -H "Content-Type: application/json" \
  -d '{"profession":"Doctor","family_size":"Small Family","current_district":"Gampaha",
       "budget":150000,"priority_safety":5,"priority_hospital":5,
       "preferred_type":"house","top_k":3}'

# Log implicit feedback (drives the Phase-7 learning job)
curl -X POST http://localhost:5000/api/users/activity \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"property_id": 42, "action": "save"}'
```

---

## Town / City Search (autocomplete)

```bash
curl "http://localhost:5000/api/locations/search?q=nug"
#   -> [ { "city": "Nugegoda", "district": "Colombo" } ]
```

---

## Location / SafeRent Score

> Start `:8004` first: `cd ai-services/location-intelligence && python app.py`

```bash
# Single district score
curl http://localhost:5000/api/location/score/Colombo

# All districts ranked
curl http://localhost:5000/api/location/all

# Compare districts
curl -X POST http://localhost:5000/api/location/compare \
  -H "Content-Type: application/json" \
  -d '{"districts": ["Colombo", "Kandy", "Galle"]}'

# Real-time prediction from current weather
curl -X POST http://localhost:5000/api/location/predict-live \
  -H "Content-Type: application/json" \
  -d '{"district": "Colombo", "rainfall_mm": 95.5, "humidity_pct": 80, "temp_avg_c": 29}'
```

---

## Admin Endpoints (admin token required)

```bash
# Dashboard analytics
curl http://localhost:5000/api/analytics/dashboard \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# List all users
curl http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Change user role
curl -X PATCH http://localhost:5000/api/admin/users/2/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "landlord"}'

# List all properties (admin view)
curl http://localhost:5000/api/admin/properties \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Scraper stats
curl http://localhost:5000/api/scraper/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Start a scrape on the server (returns 202 immediately; 409 if one is running)
curl -X POST http://localhost:5000/api/scraper/run \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"pages": 1, "district": "Colombo", "site": "ikman", "noImages": true}'

# Poll job progress (state + last 30 log lines)
curl http://localhost:5000/api/scraper/run/status \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Clear scraped listings (DESTRUCTIVE — removes all ikman/house.lk rows)
curl -X DELETE http://localhost:5000/api/scraper/clear-scraped \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## User Preferences

```bash
# Save full profile/preferences (any subset of fields; drives "For You")
curl -X PUT http://localhost:5000/api/users/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "profession": "Doctor",
    "age_group": "36-45",
    "family_size": "Small Family",
    "has_children": true,
    "has_vehicle": true,
    "current_district": "Gampaha",
    "current_rent_budget": 150000,
    "preferred_districts": ["Colombo", "Gampaha"],
    "preferred_property_type": "house",
    "priority_safety": 5, "priority_price": 3, "priority_transport": 4,
    "priority_hospital": 5, "priority_space": 4,
    "onboarding_completed": 1
  }'

# Read preferences
curl http://localhost:5000/api/users/preferences \
  -H "Authorization: Bearer $TOKEN"

# Update profile
curl -X PUT http://localhost:5000/api/users/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Menuja Test", "phone": "0771234567"}'
```

---

## Health Checks

```bash
curl http://localhost:5000/api/health        # Backend
curl http://localhost:8001/health             # Recommendation
curl http://localhost:8002/health             # Price Prediction
curl http://localhost:8003/health             # Chatbot
curl http://localhost:8004/health             # Location Intelligence
```

Expected: `{"status": "ok", "service": "..."}`

---

## Known Test Data (current DB)

| Fact | Value |
|------|-------|
| Total properties | 1,452 (as of 2026-07-08) |
| Total users | 6 (admin `mj@gmail.com` id=3) |
| Locations | 93 |
| Districts with data | Colombo (majority), Kandy, Gampaha, Matara, Galle, Kurunegala, Badulla, Kalutara, Nuwara Eliya |
| Property IDs | non-sequential — gaps from dedup/clears; query for real IDs |
| Scraped properties | ikman.lk URLs stored in `address_line` |
| Image paths | `/uploads/properties/uuid.jpg` (served via Express static) |
| Admin user ID | 3 (email: `mj@gmail.com`) |
| Test renter | Create via `POST /api/auth/register` |

## Postman Collection (quick setup)

1. Create environment variable `BASE_URL = http://localhost:5000/api`
2. Create variable `TOKEN` — auto-populate from login response: `pm.environment.set("TOKEN", pm.response.json().token)`
3. Set `Authorization: Bearer {{TOKEN}}` as a collection-level header
4. Import the curl commands above as requests
