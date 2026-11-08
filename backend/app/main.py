import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .core.config import settings
from .db.session import init_db
from .routes.health import router as health_router
from .routes.prediction import router as prediction_router
from .routes.history import router as history_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("visioncare")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager:
    Initializes database tables and verifies configuration on startup.
    """
    logger.info("VisionCare API initializing...")
    init_db()
    yield
    logger.info("VisionCare API shutting down...")


# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Digital Ophthalmic Screening Service API for evaluating retinal fundus photography across Cataract, Diabetic Retinopathy, Glaucoma, and Normal patterns.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Also ensure DB tables exist at import time
init_db()

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0]["msg"] if errors else "Invalid request data"
    logger.warning(f"Validation error on {request.url.path}: {first_error}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "type": "validation_error",
            "detail": first_error,
            "errors": errors
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "type": "internal_server_error",
            "detail": "An unexpected server error occurred while processing the request."
        }
    )

# Include Routers
app.include_router(health_router)
app.include_router(prediction_router)
app.include_router(history_router)

# Root Endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API Root Information",
    description="Returns welcome message and links to interactive documentation."
)
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "online",
        "documentation": "/docs",
        "health": "/api/health",
        "history": "/api/history"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
