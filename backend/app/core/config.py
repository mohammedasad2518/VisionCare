import json
import os
from pathlib import Path
from typing import List

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR = BASE_DIR / "app"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "VisionCare API")
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "Digital Ophthalmic Screening Platform API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Server Bindings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database Configuration (SQLite)
    DATA_DIR: Path = DATA_DIR
    DATABASE_PATH: Path = DATA_DIR / "visioncare.db"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DATABASE_PATH.as_posix()}"
    )

    # Model Configuration
    IMAGE_SIZE: tuple = (224, 224)
    CATEGORIES: list = ["Cataract", "Diabetic Retinopathy", "Glaucoma", "Normal"]

    @property
    def MODEL_PATH(self) -> Path:
        env_path = os.getenv("MODEL_PATH")
        if env_path:
            return BASE_DIR / env_path
        keras_path = MODELS_DIR / "eye_disease_model.keras"
        if keras_path.exists():
            return keras_path
        return MODELS_DIR / "eye_disease_model.h5"

    # Image Upload Validation
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024))  # 10 MB
    ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png"}
    ALLOWED_MIME_TYPES: set = {"image/jpeg", "image/png"}

    # CORS configuration
    _cors_default = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        raw = os.getenv("CORS_ORIGINS")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return self._cors_default

settings = Settings()
