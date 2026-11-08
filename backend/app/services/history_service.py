import json
import logging
from typing import Optional, List, Tuple, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.screening_record import ScreeningRecord
from ..core.config import settings

logger = logging.getLogger(__name__)


class HistoryService:
    """
    CRUD management service for persisting and retrieving screening history.
    Enforces privacy by saving metadata, timestamps, and model scores only.
    """

    @staticmethod
    def create_record(
        db: Session,
        filename: str,
        predicted_category: str,
        confidence_score: float,
        scores: Dict[str, float],
        dimensions: Union[str, Tuple[int, int]],
        image_format: str,
        file_size_bytes: int
    ) -> ScreeningRecord:
        """
        Creates and stores a new screening evaluation in the SQLite database.
        Maintains the canonical category order:
        1. Cataract
        2. Diabetic Retinopathy
        3. Glaucoma
        4. Normal
        """
        # Format dimensions consistently as 'WIDTHxHEIGHT'
        if isinstance(dimensions, (tuple, list)):
            dim_str = f"{dimensions[0]}x{dimensions[1]}"
        else:
            dim_str = str(dimensions)

        # Ensure canonical category order in serialized JSON
        ordered_scores = {}
        for cat in settings.CATEGORIES:
            if cat in scores:
                ordered_scores[cat] = round(float(scores[cat]), 4)
        for k, v in scores.items():
            if k not in ordered_scores:
                ordered_scores[k] = round(float(v), 4)

        record = ScreeningRecord(
            filename=filename,
            predicted_category=predicted_category,
            confidence_score=round(float(confidence_score), 4),
            scores_json=json.dumps(ordered_scores),
            dimensions=dim_str,
            image_format=image_format.upper(),
            file_size_bytes=int(file_size_bytes)
        )

        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"HistoryService: Created screening record ID {record.id} for '{filename}' ({predicted_category}).")
        return record

    @staticmethod
    def get_history(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None
    ) -> Tuple[List[ScreeningRecord], int]:
        """
        Retrieves paginated screening records ordered newest first.
        Optionally filters by eye condition category.
        """
        query = db.query(ScreeningRecord)

        if category and category.lower() != "all":
            query = query.filter(ScreeningRecord.predicted_category == category)

        total_count = query.count()
        records = (
            query.order_by(desc(ScreeningRecord.created_at), desc(ScreeningRecord.id))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total_count

    @staticmethod
    def get_record_by_id(db: Session, record_id: int) -> Optional[ScreeningRecord]:
        """Fetches an individual screening record by its unique database ID."""
        return db.query(ScreeningRecord).filter(ScreeningRecord.id == record_id).first()

    @staticmethod
    def delete_record(db: Session, record_id: int) -> bool:
        """Deletes a specific screening record. Returns True if deleted, False if not found."""
        record = db.query(ScreeningRecord).filter(ScreeningRecord.id == record_id).first()
        if not record:
            return False

        db.delete(record)
        db.commit()
        logger.info(f"HistoryService: Deleted screening record ID {record_id}.")
        return True

    @staticmethod
    def clear_all_records(db: Session) -> int:
        """Purges all records from the screening_records table. Returns total count deleted."""
        count = db.query(ScreeningRecord).count()
        db.query(ScreeningRecord).delete()
        db.commit()
        logger.info(f"HistoryService: Cleared all {count} screening records.")
        return count


history_service = HistoryService()

