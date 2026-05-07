# AttendAI - Face Recognition Attendance System (Appwrite Edition)

Production-ready full-stack attendance platform with:

- FastAPI AI backend (DeepFace/FaceNet embeddings, liveness, cosine similarity)
- Next.js frontend
- Appwrite Authentication + Database
- Admin + Student role-based access
- Admin-controlled attendance sessions with geofencing
- JWT-protected backend APIs

## Architecture

Next.js Frontend -> Appwrite (Auth + Database) -> FastAPI (AI Engine + Secure API)

## What Changed

- PostgreSQL runtime path removed from active API flow.
- SQLAlchemy session usage removed from active routes.
- Appwrite Python SDK now handles users and attendance storage.
- Appwrite JWT is required on all /api routes.
- Session lifecycle (start/stop/active) is now controlled by admin role.
- Attendance marking now validates geofence + face match for authenticated student.
- Face AI logic remains unchanged (embedding extraction, matching, liveness checks).

## Project Structure

```text
AttendAI/
  backend/
    main.py
    core/
      config.py
    middlewares/
      auth.py
    routes/
      register.py
      recognize.py
      attendance.py
    services/
      appwrite_client.py
      face_recognition.py
      liveness.py
    schemas/
      user.py
      recognition.py
      attendance.py
    utils/
      image.py
    requirements.txt
    .env.example

  frontend/
    app/
      page.tsx
      register/page.tsx
      attendance/page.tsx
      admin/page.tsx
      layout.tsx
      globals.css
    components/
      AuthPanel.tsx
      Navbar.tsx
      ThemeProvider.tsx
      ThemeToggle.tsx
      WebcamFeed.tsx
    lib/
      appwrite.ts
      api.ts
    types/
      index.ts
    package.json
    .env.example

  README.md
```

## Appwrite Database Setup (Step by Step)

1. Open Appwrite Console for project AttendAI.
2. Create one Database. Copy DATABASE_ID.
3. Create collection users and copy USERS_COLLECTION_ID.
4. Create collection sessions and copy SESSIONS_COLLECTION_ID.
5. Create collection attendance and copy ATTENDANCE_COLLECTION_ID.

### users collection attributes

- user_id: string, required
- name: string, required
- email: string, required
- role: string, required (admin or student)
- embedding: string array or JSON-compatible array field (required)
- created_at: datetime string, required

### sessions collection attributes

- session_id: string, required
- admin_id: string, required
- class_name: string, required
- start_time: datetime string, required
- end_time: datetime string, optional
- latitude: float, required
- longitude: float, required
- radius_meters: number, required
- is_active: boolean, required

### attendance collection attributes

- id: string, required
- user_id: string, required
- session_id: string, required
- timestamp: datetime string, required
- date: string (YYYY-MM-DD), required
- status: string, required
- distance: number, required

### Recommended indexes

users collection:

- key index on user_id
- key index on email

sessions collection:

- key index on session_id
- key index on admin_id
- key index on is_active
- key index on start_time

attendance collection:

- key index on user_id
- key index on session_id
- key index on date
- key index on timestamp

These indexes are required for fast duplicate checks and log retrieval.

## Authentication Flow

Frontend:

- Appwrite JS SDK handles signup/login/logout/session.
- Dashboard includes AuthPanel for session management.
- API wrapper requests Appwrite JWT and sends:
  Authorization: Bearer <JWT>

Backend:

- AppwriteAuthMiddleware protects all /api routes.
- Token is validated against Appwrite Account API.
- request.state.user_id is injected from verified identity.
- Frontend-provided user_id is never trusted.
- Role is loaded from Appwrite users document and enforced server-side.

## API Endpoints

Base URL: /api

- POST /register
  - Auth required
  - Body:
    {
    "images": ["data:image/jpeg;base64,...", "..."]
    }
  - Stores averaged embedding in Appwrite users collection for authenticated user.

- GET /users/me
  - Auth required
  - Returns profile with role and embedding availability.

- POST /sessions/start
  - Auth required (admin only)
  - Body:
    {
    "class_name": "Computer Networks",
    "latitude": 22.57,
    "longitude": 88.36,
    "radius_meters": 75,
    "end_time": "2026-04-08T10:45:00Z"
    }

- POST /sessions/stop
  - Auth required (admin only)
  - Body:
    {
    "session_id": "..."
    }

- GET /sessions/active
  - Auth required

- GET /sessions
  - Auth required (admin only)
  - Query params: mine, limit

- POST /recognize
  - Auth required
  - Body:
    {
    "frame": "data:image/jpeg;base64,...",
    "frames": ["data:image/jpeg;base64,..."],
    "threshold": 0.6,
    "require_liveness": true
    }
  - Loads embeddings from Appwrite users collection and runs existing matching logic.

- POST /attendance
  - Auth required
  - Body:
    {
    "session_id": "...",
    "frame": "data:image/jpeg;base64,...",
    "frames": ["data:image/jpeg;base64,...", "..."],
    "latitude": 22.57,
    "longitude": 88.36,
    "threshold": 0.6,
    "require_liveness": true
    }
  - user_id is derived from JWT and never trusted from frontend.
  - Geofence distance is validated using Haversine formula.
  - Status stored as present or denied with distance.
  - Duplicate per session per user is blocked.

- GET /attendance
  - Auth required
  - Query params: search, session_id, start_date, end_date, limit, offset, export

- GET /attendance/export
  - Auth required
  - Returns CSV.

- GET /health
  - Public

## Environment Variables

### backend/.env

Copy from backend/.env.example and set:

- APP_NAME=AttendAI Face Recognition API
- APP_ENV=development
- APP_DEBUG=true
- API_PREFIX=/api
- CORS_ORIGINS=http://localhost:3000
- APPWRITE_ENDPOINT=https://nyc.cloud.appwrite.io/v1
- APPWRITE_PROJECT_ID=69d53599001c62969125
- APPWRITE_API_KEY=<YOUR_SERVER_API_KEY>
- APPWRITE_DATABASE_ID=<DATABASE_ID>
- APPWRITE_USERS_COLLECTION_ID=<USERS_COLLECTION_ID>
- APPWRITE_SESSIONS_COLLECTION_ID=<SESSIONS_COLLECTION_ID>
- APPWRITE_ATTENDANCE_COLLECTION_ID=<ATTENDANCE_COLLECTION_ID>
- FACE_MODEL=Facenet512
- DEFAULT_SIMILARITY_THRESHOLD=0.6
- FRAME_PROCESS_STRIDE=3
- MAX_FRAME_WIDTH=640
- LIVENESS_MIN_FRAMES=6
- LIVENESS_MIN_DISPLACEMENT=15
- CACHE_BACKGROUND_REFRESH_ENABLED=true
- TRUST_PROXY_HEADERS=false
- TRUSTED_PROXY_COUNT=0
- MAX_REQUEST_BYTES=8388608
- MAX_IMAGE_BYTES=2097152
- MAX_IMAGE_WIDTH=1280
- MAX_IMAGE_HEIGHT=720
- ALLOWED_IMAGE_MIME_TYPES_RAW=image/jpeg,image/png
- MIN_FACE_BRIGHTNESS=45
- LOW_LIGHT_BOOST_THRESHOLD=75
- MAX_FACE_CENTER_OFFSET_RATIO=0.35

### frontend/.env

Copy from frontend/.env.example and set:

- NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
- NEXT_PUBLIC_APPWRITE_PROJECT_ID=69d53599001c62969125
- NEXT_PUBLIC_APPWRITE_PROJECT_NAME=AttendAI
- NEXT_PUBLIC_APPWRITE_ENDPOINT=https://nyc.cloud.appwrite.io/v1

## Local Run

Backend:

```bash
cd backend
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://localhost:3000

## Security Notes

- All /api endpoints except /health are JWT-protected.
- Backend never accepts user_id from frontend for attendance.
- Only admin role can create and stop sessions.
- Geofence validation is enforced server-side.
- Duplicate attendance per user/session is enforced in Appwrite data checks.
- For production hardening add role-based route authorization and request rate limiting.
