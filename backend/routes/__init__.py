from routes.attendance import router as attendance_router
from routes.recognize import router as recognize_router
from routes.register import router as register_router
from routes.sessions import router as sessions_router
from routes.users import router as users_router

__all__ = ["register_router", "recognize_router", "attendance_router", "sessions_router", "users_router"]
