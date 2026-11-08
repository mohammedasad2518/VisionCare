import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Query, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services.image_service import image_service
from ..services.model_service import model_service
from ..services.gradcam_service import gradcam_service
from ..services.history_service import history_service
from ..schemas.prediction import (
    PredictionSuccessResponse,
    GradCAMResponseSchema,
    ServiceUnavailableResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Screening & Inference"])


@router.post(
    "/predict",
    response_model=PredictionSuccessResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Validation error (invalid format, oversized file, or corrupt stream)"
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ServiceUnavailableResponse,
            "description": "Model is not configured or weights are unavailable"
        }
    },
    summary="Evaluate Retinal Fundus Image",
    description="Validates a digital retinal fundus photograph, routes it to the VGG19 classification model, and archives the screening evaluation in the SQLite database."
)
async def predict_retinal_disease(
    file: UploadFile = File(..., description="Digital retinal fundus photograph (JPG, JPEG, or PNG, max 10 MB)"),
    db: Session = Depends(get_db)
):
    """
    1. Validates file format, size, dimensions, and readability using ImageService.
    2. Checks model availability.
    3. If model is unavailable, returns HTTP 503.
    4. Routes preprocessed RGB tensor to VGG19 and returns classification scores.
    5. Archives the successful evaluation in SQLite database history.
    """
    # 1. Full Image Validation
    validated_image = await image_service.validate_and_process(file)

    # 2. Model Availability Check
    if not model_service.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Screening service is temporarily unavailable because the classification model has not been configured."
        )

    # 3. Model Inference Execution
    inference_result = model_service.predict(validated_image.image)

    # 4. Save to Persistent Screening History (SQLite)
    screening_record = None
    try:
        screening_record = history_service.create_record(
            db=db,
            filename=validated_image.filename,
            predicted_category=inference_result["prediction"],
            confidence_score=inference_result["confidence"],
            scores=inference_result["probabilities"],
            dimensions=validated_image.dimensions,
            image_format=validated_image.format,
            file_size_bytes=validated_image.size_bytes
        )
    except Exception as e:
        logger.error(f"Failed to record screening evaluation in database: {e}", exc_info=True)
        # Note: Do not abort the clinical result if archiving encounters an issue

    return PredictionSuccessResponse(
        status="success",
        message="Retinal image evaluated successfully.",
        screening_id=screening_record.id if screening_record else None,
        image={
            "filename": validated_image.filename,
            "size_bytes": validated_image.size_bytes,
            "dimensions": validated_image.dimensions,
            "format": validated_image.format
        },
        prediction=inference_result["prediction"],
        confidence=inference_result["confidence"],
        scores=inference_result["probabilities"],
        probabilities=inference_result["probabilities"]
    )


@router.post(
    "/gradcam",
    response_model=GradCAMResponseSchema,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Validation error (invalid format, oversized file, or corrupt stream)"
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ServiceUnavailableResponse,
            "description": "Model is not configured or weights are unavailable"
        }
    },
    summary="Generate Grad-CAM Visual Explanation",
    description="Calculates gradient-weighted class activation mapping (Grad-CAM) heatmaps and overlays for a retinal photograph."
)
async def generate_gradcam_explanation(
    file: UploadFile = File(..., description="Digital retinal fundus photograph (JPG, JPEG, or PNG, max 10 MB)"),
    class_index: Optional[int] = Query(None, description="Target category index (0-3). Defaults to the model's top predicted class.")
):
    """
    1. Validates the uploaded fundus photograph.
    2. Verifies classification model availability.
    3. Computes genuine gradients from layer 'block5_conv4' using tf.GradientTape.
    4. Generates bicubic resized heatmap and overlay, encoded as Base64 PNG data URLs.
    """
    # 1. Image Validation
    validated_image = await image_service.validate_and_process(file)

    # 2. Model Availability Check
    if not model_service.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Screening service is temporarily unavailable because the classification model has not been configured."
        )

    # 3. Grad-CAM Calculation
    try:
        gradcam_result = gradcam_service.generate_gradcam(
            validated_image.image,
            class_index=class_index
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(re)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during Grad-CAM visualization generation: {str(e)}"
        )

    return GradCAMResponseSchema(**gradcam_result)
