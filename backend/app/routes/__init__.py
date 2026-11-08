"""
API Routes Package
"""
from .health import router as health_router
from .prediction import router as prediction_router
from .history import router as history_router

__all__ = ["health_router", "prediction_router", "history_router"]
