# API.md — SmartRentAI Backend Endpoints

Base URL: `http://localhost:5000/api`
Auth: `Authorization: Bearer <jwt_token>`
Rate limits: see CLAUDE.md → Rate Limiting section.

---

## Auth `/api/auth`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | None | Create new account |
| POST | `/auth/login` | None | Login, returns JWT |
| GET | `/auth/me` | Required | Get current user profile |
| PUT | `/auth/change-password` | Required | Change own password |

### POST `/auth/register`
```json
Body: { "full_name": "string(2-100)", "email": "string", "password": "string(min 6)", "role": "renter|landlord" }
201: { "message": "Registration successful", "token": "jwt", "user": { id, full_name, email, role } }
409: { "error": "Email already registered" }
422: { "errors": [...] }
```

### POST `/auth/login`
```json
Body: { "email": "string", "password": "string" }
200: { "token": "jwt", "user": { id, full_name, email, role, avatar_url } }
401: { "error": "Invalid credentials" }
```

### GET `/auth/me`
```json
200: { id, full_name, email, role, avatar_url, phone, created_at }
```

### PUT `/auth/change-password`
```json
Body: { "current_password": "string", "new_password": "string(min 6)" }
200: { "message": "Password updated successfully" }
400: { "error": "Current password incorrect" }
```

---

## Properties `/api/properties`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/properties` | None | Search/list properties |
| GET | `/properties/saved` | Required | Get user's wishlist |
| GET | `/properties/:id` | None | Get single property (increments views) |
| POST | `/properties` | landlord\|admin | Create property with image upload |
| PUT | `/properties/:id` | Owner\|admin | Update property fields |
| DELETE | `/properties/:id` | Owner\|admin | Delete property |
| POST | `/properties/:id/save` | Required | Toggle wishlist (save/unsave) |

### GET `/properties` — Query Params
| Param | Type | Example |
|-------|------|---------|
| `search` | string | `"colombo house"` — FULLTEXT boolean mode |
| `city` | string | `"Colombo"` |
| `district` | string | `"Colombo"` |
| `type` | string | `apartment\|house\|room\|villa\|commercial` |
| `min_rent` | number | `30000` |
| `max_rent` | number | `200000` |
| `bedrooms` | number | `3` |
| `furnished` | string | `unfurnished\|semi-furnished\|furnished` |
| `sort` | string | `created_at\|rent_asc\|rent_desc` |
| `page` | number | `1` (default) |
| `limit` | number | `12` (default) |

```json
200: { "data": [...properties], "total": 1452, "page": 1, "total_pages": 121 }
```

### GET `/properties/:id`
```json
200: { ...property, "images": [...], "amenities": [...], "reviews": [...last 5] }
404: { "error": "Property not found" }
```

### POST `/properties`
```
Content-Type: multipart/form-data
Images: field name "images", max 10 files, 5MB each, jpeg/jpg/png/webp
Body fields: title(5-200), description(min 20), property_type, bedrooms(0-20),
             bathrooms(0-20), monthly_rent, address_line, city, district,
             [area_sqft, deposit, latitude, longitude, furnished, available_from,
              province, amenity_ids (JSON array)]
201: { "message": "Property created", "id": 123 }
```

### PUT `/properties/:id`
```json
Body (any subset): { title, description, monthly_rent, deposit, bedrooms,
                     bathrooms, area_sqft, furnished, available_from, status, address_line }
200: { "message": "Property updated" }
403: { "error": "Access denied" }
```

### POST `/properties/:id/save`
```json
200: { "saved": true }   // added to wishlist
200: { "saved": false }  // removed from wishlist
```

---

## Predictions `/api/predictions`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/predictions/price` | None | Predict monthly rent |
| GET | `/predictions/history` | Required | Get user's past predictions |

### POST `/predictions/price`
Model: CatBoost, trained on 820 real scraped/manual listings (see AI_MODELS.md → Service 2).
`area_sqft`/`has_parking`/`has_pool`/`has_gym` are **not** used by the current model —
sending them is harmless but they're ignored.
```json
Body: { "district": "Colombo", "property_type": "apartment", "bedrooms": 2,
        "bathrooms": 1, "furnished": "semi-furnished" }
200: { "predicted_price": 190337.54,
       "price_range": { "low": 0, "high": 406251.93 },
       "confidence": 0.6689, "confidence_interval": 215914.39,
       "model_info": { "name": "CatBoost", "mae": 91678.65, "r2": 0.4689,
                        "cv_r2": 0.4711, "training_samples": 820 },
       "top_3_factors": ["Location (Colombo) — strongest price driver", "..."],
       "model_version": "2.0-real-data" }
503: { "error": "Price prediction service offline" }
```

---

## Chatbot `/api/chatbot`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/chatbot/message` | None | Send message, get AI reply |
| GET | `/chatbot/history/:session_id` | Required | Get session history |

### POST `/chatbot/message`
```json
Body: { "message": "What are houses for rent in Colombo?",
        "session_id": "uuid-string",
        "user_id": 3 }
200: { "reply": "string", "intent": "search_property", "confidence": 0.92 }
503: { "error": "Chatbot service offline" }
```

---

## Recommendations `/api/recommendations`
Profile-based "For You". Proxies to the recommendation service at `:8001`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/recommendations` | Required | Personalised "For You" list (from profile) |
| GET | `/recommendations/insights` | Required | What the model inferred for this user |
| GET | `/recommendations/similar/:id` | None | Properties similar to given id |

### GET `/recommendations`
Builds a profile from the user's `user_preferences` row, calls `:8001/recommend`,
and enriches results with full property details (image, etc.).
```json
200 (no profile yet):
  { "needs_onboarding": true, "recommendations": [], "profile_summary": null }

200 (with profile):
{
  "needs_onboarding": false,
  "profile_summary": "Based on your profile as a Doctor with a family of 3-4, ...",
  "criteria": { "matched_property_type": "house", "min_saferent_score": 77.8, ... },
  "recommendations": [
    { "id": 42, "title": "...", "district": "Colombo", "monthly_rent": 145000,
      "bedrooms": 3, "primary_image": "/uploads/...",
      "match_score": 0.94, "saferent_score": 71.2,
      "match_reasons": ["High SafeRent score matches your safety priority", ...] }
  ]
}
503: { "error": "Recommendation service offline", "recommendations": [] }
```

### GET `/recommendations/insights`
```json
200: {
  "user_id": 5,
  "inferred_criteria": { "matched_property_type": "house", "max_price": 147000, ... },
  "explanation": ["Ideal property type: house", "Minimum SafeRent score: 67/100", ...],
  "profile_summary": "string",
  "priorities_used": { "safety": 5, "price": 3, "transport": 4, "hospital": 5, "space": 4 }
}
```

---

## Locations `/api/locations`
DB-backed town/city lookup (separate from the SafeRent proxy at `/api/location`).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/locations/search?q=` | None | Autocomplete of `{ city, district }` from the locations table |

### GET `/locations/search?q=nug`
```json
200: [ { "city": "Nugegoda", "district": "Colombo" } ]
```

---

## Location / SafeRent `/api/location`
Proxies to Location Intelligence service at `:8004`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/location/score/:district` | None | SafeRent score for one district |
| GET | `/location/all` | None | All 25 districts ranked |
| POST | `/location/compare` | None | Side-by-side comparison |
| POST | `/location/predict-live` | None | Real-time disaster probability |

### GET `/location/score/:district`
```json
200: { "district": "Colombo", "safe_score": 74, "category": "Good",
       "breakdown": { "disaster": 80, "flood": 70, "landslide": 85,
                      "hospital": 90, "transport": 95, "crime": 65, "rainfall": 60 } }
503: { "error": "Location intelligence service offline" }
```

### POST `/location/compare`
```json
Body: { "districts": ["Colombo", "Kandy", "Galle"] }
200: { "comparison": [...scored districts] }
```

### POST `/location/predict-live`
```json
Body: { "district": "Colombo", "rainfall_mm": 120.5,
        "humidity_pct": 85, "temp_avg_c": 28.5 }
200: { "disaster_probability": 0.23, "risk_level": "Low" }
```

---

## Analytics `/api/analytics` — Admin only

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/analytics/dashboard` | admin | Full dashboard stats |
| POST | `/analytics/log` | None | Log a frontend event |

### GET `/analytics/dashboard`
```json
200: {
  "stats": { "total_users": 6, "total_properties": 1452,
             "total_predictions": 36, "total_chats": 5 },
  "role_breakdown": [{ "role": "admin", "count": 1 }, ...],
  "top_cities": [{ "city": "Colombo", "listings": 450, "avg_rent": 95000 }, ...],
  "rent_trend": [{ "month": "2026-06", "avg_rent": 87000, "new_listings": 206 }, ...],
  "recent_activity": [...]
}
```

### POST `/analytics/log`
```json
Body: { "event_type": "property_view", "property_id": 5, "meta": {} }
200: { "ok": true }
```

---

## Admin `/api/admin` — Admin only

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/users` | admin | List all users |
| PATCH | `/admin/users/:id/role` | admin | Change user role |
| DELETE | `/admin/users/:id` | admin | Delete user |
| GET | `/admin/properties` | admin | List all properties |
| PATCH | `/admin/properties/:id/status` | admin | Change property status |

### PATCH `/admin/users/:id/role`
```json
Body: { "role": "renter|landlord|admin" }
200: { "message": "Role updated" }
```

### PATCH `/admin/properties/:id/status`
```json
Body: { "status": "available|rented|inactive" }
200: { "message": "Status updated" }
```

---

## Users `/api/users` — Authenticated

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users/preferences` | Required | Get full profile + preferences |
| PUT | `/users/preferences` | Required | Save profile/preferences (partial OK) |
| POST | `/users/activity` | Required | Log implicit feedback (view/save/enquiry) |
| PUT | `/users/profile` | Required | Update name/phone |

### PUT `/users/preferences`
Whitelist-upsert: send any subset of the fields below (supports per-step saves).
`preferred_districts` accepts an array (stored as CSV).
```json
Body: {
  "profession": "Doctor", "age_group": "36-45", "family_size": "Small Family",
  "has_children": true, "has_vehicle": true,
  "current_district": "Gampaha", "current_city": "Negombo", "current_rent_budget": 150000,
  "preferred_districts": ["Colombo","Gampaha"], "preferred_property_type": "house",
  "priority_safety": 5, "priority_price": 3, "priority_transport": 4,
  "priority_hospital": 5, "priority_space": 4, "onboarding_completed": 1
}
200: { "message": "Preferences saved" }
```

### POST `/users/activity`
```json
Body: { "property_id": 42, "action": "view" }   // action: view | save | enquiry
200: { "logged": true }
```

### PUT `/users/profile`
```json
Body: { "full_name": "string", "phone": "string" }
200: { "message": "Profile updated" }
```

---

## Scraper `/api/scraper` — Admin only

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/scraper/stats` | admin | Summary + district breakdown + recent 20 |
| POST | `/scraper/run` | admin | Start a scrape on the server (one at a time) |
| GET | `/scraper/run/status` | admin | Current/last job state + last 30 log lines |
| DELETE | `/scraper/clear-scraped` | admin | Delete all ikman/house.lk listings |

### POST `/scraper/run`
Spawns `python scraper.py` on the server with validated args (district whitelist,
`site ∈ {all,ikman,houselk}`, `pages` clamped 1–5). Returns immediately.
```json
Body: { "pages": 2, "district": "Colombo", "site": "all", "noImages": true }
202:  { "started": true, "args": { "pages": 2, "district": "Colombo", "site": "all", "noImages": true } }
409:  { "error": "A scrape is already running", "job": {...} }
```

### GET `/scraper/run/status`
```json
200: { "running": false, "startedAt": "...", "finishedAt": "...",
       "args": {...}, "code": 0, "saved": 18, "skipped": 4,
       "error": null, "tail": ["...last 30 log lines..."] }
```
> Requires Python on the server's PATH. If `python` isn't found, set `PYTHON_BIN`
> in `backend/.env`.

### GET `/scraper/stats`
```json
200: {
  "summary": { "total": 1452, "scraped": 1451, "manual": 1 },
  "by_district": [{ "district": "Colombo", "count": 450, "avg_rent": 95000, "scraped": 448 }],
  "recent": [{ "id": 5, "title": "...", "monthly_rent": 75000,
               "property_type": "house", "district": "Colombo",
               "address_line": "https://ikman.lk/...", "image": "/uploads/...", "created_at": "..." }]
}
```

### DELETE `/scraper/clear-scraped`
```json
200: { "deleted": 1451 }
```

---

## Health Check

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Server status |

```json
200: { "status": "ok", "service": "SmartRentAI API", "version": "1.0.0" }
```

---

## Error Responses (common)

| Code | Meaning |
|------|---------|
| 400 | Bad request / validation failed |
| 401 | Missing or expired JWT |
| 403 | Authenticated but wrong role |
| 404 | Resource not found |
| 422 | Validation errors array |
| 429 | Rate limit hit (auth route only) |
| 503 | AI microservice offline |
| 500 | Server error |
