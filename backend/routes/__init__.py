from routes.attendance import router as attendance_router
from routes.recognize import router as recognize_router
from routes.register import router as register_router

__all__ = ["register_router", "recognize_router", "attendance_router"]
