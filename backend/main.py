from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from middlewares import AppwriteAuthMiddleware
from routes import attendance_router, recognize_router, register_router, sessions_router, users_router

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.app_debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AppwriteAuthMiddleware)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.app_name}


app.include_router(register_router, prefix=settings.api_prefix)
app.include_router(recognize_router, prefix=settings.api_prefix)
app.include_router(attendance_router, prefix=settings.api_prefix)
app.include_router(sessions_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
