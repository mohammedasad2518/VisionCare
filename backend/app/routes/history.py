import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..db.session import get_db
from ..services.history_service import history_service
from ..schemas.history import (
    ScreeningRecordSchema,
    HistoryListResponse,
    DeleteRecordResponse,
    ClearHistoryResponse,
    HistoryNotFoundResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["Screening History Archive"])


@router.get(
    "",
    response_model=HistoryListResponse,
    summary="List Screening History Records",
    description="Returns a paginated list of archived retinal screening evaluations, ordered newest first."
)
def list_screening_history(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    category: Optional[str] = Query(None, description="Filter by classified condition (Cataract, Diabetic Retinopathy, Glaucoma, Normal)"),
    db: Session = Depends(get_db)
):
    try:
        records, total_count = history_service.get_history(
            db=db,
            skip=skip,
            limit=limit,
            category=category
        )
        return HistoryListResponse(
            status="success",
            total_count=total_count,
            records=[ScreeningRecordSchema(**r.to_dict()) for r in records]
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error in list_screening_history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while retrieving screening history."
        )


@router.get(
    "/{screening_id}",
    response_model=ScreeningRecordSchema,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": HistoryNotFoundResponse,
            "description": "Screening record not found"
        }
    },
    summary="Get Single Screening Record",
    description="Retrieves full details of a specific screening record by its unique identifier."
)
def get_screening_record(
    screening_id: int,
    db: Session = Depends(get_db)
):
    if screening_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Screening ID must be a positive integer."
        )

    try:
        record = history_service.get_record_by_id(db=db, record_id=screening_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Screening record with ID {screening_id} was not found."
            )
        return ScreeningRecordSchema(**record.to_dict())
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_screening_record({screening_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while retrieving the screening record."
        )


@router.delete(
    "/{screening_id}",
    response_model=DeleteRecordResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": HistoryNotFoundResponse,
            "description": "Screening record not found"
        }
    },
    summary="Delete Single Screening Record",
    description="Deletes a specific screening record from the database archive."
)
def delete_screening_record(
    screening_id: int,
    db: Session = Depends(get_db)
):
    if screening_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Screening ID must be a positive integer."
        )

    try:
        deleted = history_service.delete_record(db=db, record_id=screening_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Screening record with ID {screening_id} was not found."
            )
        return DeleteRecordResponse(
            status="success",
            message=f"Screening record ID {screening_id} deleted successfully.",
            deleted_id=screening_id
        )
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_screening_record({screening_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while deleting the screening record."
        )


@router.delete(
    "",
    response_model=ClearHistoryResponse,
    summary="Clear All Screening History",
    description="Permanently deletes all archived screening records from the database."
)
def clear_screening_history(
    db: Session = Depends(get_db)
):
    try:
        deleted_count = history_service.clear_all_records(db=db)
        return ClearHistoryResponse(
            status="success",
            message=f"Successfully cleared {deleted_count} screening history records.",
            deleted_count=deleted_count
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error in clear_screening_history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while clearing screening history."
        )

