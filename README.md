# AttendAI - Face Recognition Attendance System (Appwrite Edition)

Production-ready full-stack attendance platform with:

- FastAPI AI backend (DeepFace/FaceNet embeddings, liveness, cosine similarity)
- Next.js frontend
- Appwrite Authentication + Database
- JWT-protected backend APIs

## Architecture

Next.js Frontend -> Appwrite (Auth + Database) -> FastAPI (AI Engine + Secure API)

## What Changed

- PostgreSQL runtime path removed from active API flow.
- SQLAlchemy session usage removed from active routes.
- Appwrite Python SDK now handles users and attendance storage.
- Appwrite JWT is required on all /api routes.
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
4. Create collection attendance and copy ATTENDANCE_COLLECTION_ID.

### users collection attributes

- user_id: string, required
- name: string, required
- email: string, required
- embedding: string array or JSON-compatible array field (required)
- created_at: datetime string, required

### attendance collection attributes

- id: string, required
- user_id: string, required
- timestamp: datetime string, required
- date: string (YYYY-MM-DD), required
- status: string, required

### Recommended indexes

users collection:

- key index on user_id
- key index on email

attendance collection:

- key index on user_id
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

## API Endpoints

Base URL: /api

- POST /register
  - Auth required
  - Body:
    {
    "images": ["data:image/jpeg;base64,...", "..."]
    }
  - Stores averaged embedding in Appwrite users collection for authenticated user.

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
    "status": "present"
    }
  - user_id is derived from JWT.
  - Duplicate same-day attendance is blocked.

- GET /attendance
  - Auth required
  - Query params: search, start_date, end_date, limit, offset, export

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
- APPWRITE_ATTENDANCE_COLLECTION_ID=<ATTENDANCE_COLLECTION_ID>
- FACE_MODEL=Facenet512
- DEFAULT_SIMILARITY_THRESHOLD=0.6
- FRAME_PROCESS_STRIDE=3
- MAX_FRAME_WIDTH=640
- LIVENESS_MIN_FRAMES=6
- LIVENESS_MIN_DISPLACEMENT=15

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
- Duplicate attendance per user/day is enforced in Appwrite data checks.
- For production hardening add role-based route authorization and request rate limiting.
