from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

class ModelStatusSchema(BaseModel):
    available: bool = Field(..., description="Whether the trained VGG19 model is currently loaded and functional")
    model_path: str = Field(..., description="Configured file path to model weights")
    file_exists: bool = Field(..., description="Whether the model weights file exists on disk")
    tensorflow_installed: bool = Field(..., description="Whether TensorFlow is installed in the Python environment")
    architecture: str = Field(..., description="Model architecture identification")
    categories: list[str] = Field(..., description="Target eye condition categories")
    error: Optional[str] = Field(None, description="Diagnostic message if model is unavailable")

class HealthResponse(BaseModel):
    status: str = Field(..., example="healthy")
    app_name: str = Field(..., example="VisionCare API")
    version: str = Field(..., example="1.0.0")
    model: ModelStatusSchema

class ImageMetadataSchema(BaseModel):
    filename: str
    size_bytes: int
    dimensions: Tuple[int, int]
    format: str

class PredictionSuccessResponse(BaseModel):
    status: str = "success"
    message: str
    screening_id: Optional[int] = Field(None, description="Unique screening archive identifier")
    image: ImageMetadataSchema
    prediction: str
    confidence: float
    scores: Dict[str, float] = Field(..., description="Model output scores across all four eye categories")
    probabilities: Dict[str, float] = Field(..., description="Distribution scores across all categories")

class GradCAMResponseSchema(BaseModel):
    status: str = "success"
    message: str = "Grad-CAM visual explanation generated successfully."
    prediction: str = Field(..., description="Class name evaluated by the model")
    class_index: int = Field(..., description="Index of the evaluated class")
    confidence: float = Field(..., description="Model score for the evaluated class")
    target_layer: str = Field(..., description="Convolutional feature layer used for Grad-CAM backpropagation")
    heatmap_data_url: str = Field(..., description="Base64 PNG data URL of the standalone heatmap")
    overlay_data_url: str = Field(..., description="Base64 PNG data URL of the heatmap blended onto the original image")
    original_dimensions: Tuple[int, int] = Field(..., description="Original width and height of the image")
    scores: Dict[str, float] = Field(..., description="Model output scores across all four eye categories")

class ServiceUnavailableResponse(BaseModel):
    detail: str = Field(
        "Screening service is temporarily unavailable because the classification model has not been configured.",
        example="Screening service is temporarily unavailable because the classification model has not been configured."
    )
