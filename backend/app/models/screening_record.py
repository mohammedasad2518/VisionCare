import json
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from ..db.session import Base
from ..core.config import settings

class ScreeningRecord(Base):
    """
    SQLAlchemy model representing a persistent record of a completed retinal screening.
    Stores metadata, model scores, and timestamps.
    Does NOT store raw image files or blobs to respect user privacy and storage bounds.
    """
    __tablename__ = "screening_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    predicted_category = Column(String(64), nullable=False, index=True)
    confidence_score = Column(Float, nullable=False)
    scores_json = Column(Text, nullable=False)  # JSON-encoded dictionary of category scores
    dimensions = Column(String(32), nullable=False)  # e.g. "512x512"
    image_format = Column(String(16), nullable=False)  # e.g. "JPEG", "PNG"
    file_size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    @property
    def scores(self) -> Dict[str, float]:
        """
        Deserializes the scores JSON dictionary ensuring the exact 4-category order:
        1. Cataract
        2. Diabetic Retinopathy
        3. Glaucoma
        4. Normal
        """
        try:
            raw = json.loads(self.scores_json)
            # Guarantee strict canonical ordering
            ordered = {}
            for cat in settings.CATEGORIES:
                if cat in raw:
                    ordered[cat] = float(raw[cat])
            # Include any remaining keys if applicable
            for k, v in raw.items():
                if k not in ordered:
                    ordered[k] = float(v)
            return ordered
        except Exception:
            return {}

    def to_dict(self) -> Dict[str, Any]:
        """Converts database record into a clean dictionary for Pydantic serialization."""
        return {
            "id": self.id,
            "filename": self.filename,
            "predicted_category": self.predicted_category,
            "confidence_score": round(self.confidence_score, 4),
            "scores": self.scores,
            "dimensions": self.dimensions,
            "image_format": self.image_format,
            "file_size_bytes": self.file_size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

