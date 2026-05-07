# AttendAI — Deployment Guide

## Architecture

```
Vercel (Frontend: Next.js)
    │ HTTPS
    ▼
Render (Backend: FastAPI + uvicorn)
    │ Appwrite SDK (server key)
    ▼
Appwrite Cloud (Auth + Database + Storage)
```

---

## Prerequisites

| Service | Free Tier | URL |
|---------|-----------|-----|
| Appwrite Cloud | ✅ Yes | https://appwrite.io |
| Render | ✅ Yes (750 h/mo) | https://render.com |
| Vercel | ✅ Yes | https://vercel.com |

---

## 1 — Appwrite Setup

### 1.1 Create a project
1. Go to https://cloud.appwrite.io — create a new project.
2. Note your **Project ID**.

### 1.2 Create a Database
1. Databases → Create database → Note the **Database ID**.

### 1.3 Create Collections

#### `users` collection
| Attribute | Type | Required | Default |
|-----------|------|----------|---------|
| `user_id` | String (255) | ✅ | — |
| `name` | String (255) | ✅ | — |
| `email` | String (255) | ✅ | — |
| `role` | String (20) | ✅ | `student` |
| `embedding` | Float[] (array) | ❌ | `[]` |
| `created_at` | String (50) | ❌ | — |

**Permissions**: Any authenticated user can read their own document. Server key can read/write all.

#### `sessions` collection
| Attribute | Type | Required |
|-----------|------|----------|
| `session_id` | String (255) | ✅ |
| `admin_id` | String (255) | ✅ |
| `class_name` | String (255) | ✅ |
| `start_time` | String (50) | ✅ |
| `end_time` | String (50) | ❌ |
| `latitude` | Float | ✅ |
| `longitude` | Float | ✅ |
| `radius_meters` | Float | ✅ |
| `is_active` | Boolean | ✅ |

> [!IMPORTANT]
> Enable **Realtime** on the sessions collection. Frontend subscribes to this for instant session popups.

#### `attendance` collection
| Attribute | Type | Required |
|-----------|------|----------|
| `id` | String (255) | ✅ |
| `user_id` | String (255) | ✅ |
| `session_id` | String (255) | ❌ |
| `timestamp` | String (50) | ✅ |
| `date` | String (20) | ✅ |
| `status` | String (20) | ✅ |
| `distance` | Float | ❌ |

### 1.4 Get an API Key
Security → API Keys → Create API key with **Databases** read/write scope.

---

## 2 — Backend Deployment (Render)

### 2.1 Create a Web Service
1. Render dashboard → New → Web Service.
2. Connect your GitHub repo, set **Root Directory** to `backend`.
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Instance type**: Free (or Starter for persistent memory / faster cold start).

> [!WARNING]
> Free Render instances **spin down** after 15 minutes of inactivity. The first request after spin-down triggers a cold start that reloads DeepFace models (can take 30–60 s). Use a paid plan or a cron ping for production.

### 2.2 Environment Variables

Set these in Render → Environment:

```
APP_ENV=production
APP_DEBUG=false
API_PREFIX=/api
CORS_ORIGINS=https://your-app.vercel.app
APPWRITE_ENDPOINT=https://nyc.cloud.appwrite.io/v1
APPWRITE_PROJECT_ID=<your_project_id>
APPWRITE_API_KEY=<your_server_api_key>
APPWRITE_DATABASE_ID=<your_database_id>
APPWRITE_USERS_COLLECTION_ID=<users_collection_id>
APPWRITE_SESSIONS_COLLECTION_ID=<sessions_collection_id>
APPWRITE_ATTENDANCE_COLLECTION_ID=<attendance_collection_id>
FACE_MODEL=Facenet512
DEFAULT_SIMILARITY_THRESHOLD=0.6
FRAME_PROCESS_STRIDE=3
MAX_FRAME_WIDTH=640
LIVENESS_MIN_FRAMES=6
LIVENESS_MIN_DISPLACEMENT=15
CACHE_REFRESH_INTERVAL_MINUTES=10
GEOFENCE_BUFFER_METERS=10
GPS_ACCURACY_LIMIT_METERS=50
RATE_LIMIT_ATTENDANCE=10/minute
RATE_LIMIT_RECOGNIZE=20/minute
```

### 2.3 Dockerfile (already in `backend/Dockerfile`)

The existing Dockerfile is used automatically by Render if detected.

---

## 3 — Frontend Deployment (Vercel)

### 3.1 Import Project
1. Vercel dashboard → Add New Project → Import from GitHub.
2. **Root Directory**: `frontend`
3. **Framework Preset**: Next.js (auto-detected)
4. **Build Command**: `npm run build`
5. **Output Directory**: `.next`

### 3.2 Environment Variables

Set these in Vercel → Settings → Environment Variables:

```
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com/api
NEXT_PUBLIC_APPWRITE_ENDPOINT=https://nyc.cloud.appwrite.io/v1
NEXT_PUBLIC_APPWRITE_PROJECT_ID=<your_project_id>
NEXT_PUBLIC_APPWRITE_DATABASE_ID=<your_database_id>
NEXT_PUBLIC_APPWRITE_SESSIONS_COLLECTION_ID=<sessions_collection_id>
```

> [!IMPORTANT]
> Variables prefixed `NEXT_PUBLIC_` are exposed to the browser. Do not put your Appwrite server API key here.

---

## 4 — CORS Configuration

In the backend `CORS_ORIGINS`, set **exactly** the Vercel deployment URL:
```
CORS_ORIGINS=https://your-app.vercel.app
```

For multiple environments (preview + prod):
```
CORS_ORIGINS=https://your-app.vercel.app,https://your-preview-url.vercel.app
```

In Appwrite Console → your project → Settings → Platforms:
- Add a **Web** platform with hostname `your-app.vercel.app`.

---

## 5 — Running Locally

### Backend
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate        # Windows
source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
cp .env.example .env            # Fill in your values
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local      # Fill in your values
npm run dev
```

### Docker Compose (both services together)
```bash
# From repo root — fill .env files first
docker-compose up --build
```

---

## 6 — Running Tests

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## 7 — Making a User an Admin

1. In Appwrite Console → Databases → your database → `users` collection.
2. Find the document with the user's `user_id`.
3. Set the `role` attribute to `admin`.

---

## 8 — Summary of New Production Features

| Feature | Implementation |
|---------|---------------|
| In-memory embedding cache | `services/cache.py` — TTL 10 min, startup preload |
| Rate limiting | `slowapi` — 10/min on `/attendance`, 20/min on `/recognize` |
| GPS accuracy validation | Rejects if `gps_accuracy > 50m` → `LOW_GPS_ACCURACY` |
| Geofence buffer | `effective_radius = radius + 10m` |
| Structured error codes | `OUT_OF_RANGE`, `FACE_NOT_DETECTED`, `LIVENESS_FAILED`, `FACE_MISMATCH` |
| Multi-face rejection | Rejects frames with >1 face detected |
| Appwrite Realtime | Session popup on student page — zero polling |
| Admin analytics | Pie + bar charts, stat cards |
| Structured logging | JSON-like `key=value` log lines, recognition events |
| Dead code removed | `database/`, `models/`, `services/attendance.py` deleted |
| Test suite | `pytest` — 10 test cases covering all main paths |
