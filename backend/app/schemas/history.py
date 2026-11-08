from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class ScreeningRecordSchema(BaseModel):
    id: int = Field(..., description="Unique screening identifier")
    filename: str = Field(..., description="Original name of the uploaded retinal photograph")
    predicted_category: str = Field(..., description="Classified eye health condition")
    confidence_score: float = Field(..., description="Model confidence score for the primary category")
    scores: Dict[str, float] = Field(..., description="Model scores distribution across all four categories in canonical order")
    dimensions: str = Field(..., description="Image resolution (width x height)")
    image_format: str = Field(..., description="Format format of the uploaded photograph")
    file_size_bytes: int = Field(..., description="File size in bytes")
    created_at: str = Field(..., description="Timestamp in ISO 8601 UTC format")

    class Config:
        from_attributes = True


class HistoryListResponse(BaseModel):
    status: str = "success"
    total_count: int = Field(..., description="Total number of archived screening records")
    records: List[ScreeningRecordSchema] = Field(..., description="List of screening records, ordered newest first")


class DeleteRecordResponse(BaseModel):
    status: str = "success"
    message: str = Field(..., example="Screening record deleted successfully.")
    deleted_id: int = Field(..., description="Identifier of the removed screening record")


class ClearHistoryResponse(BaseModel):
    status: str = "success"
    message: str = Field(..., example="All screening history records have been cleared.")
    deleted_count: int = Field(..., description="Total number of deleted screening records")


class HistoryNotFoundResponse(BaseModel):
    detail: str = Field(..., example="Screening record with ID 1 was not found.")

