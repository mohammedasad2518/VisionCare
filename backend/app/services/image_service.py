import io
from dataclasses import dataclass
from typing import Tuple
from PIL import Image, UnidentifiedImageError
from fastapi import UploadFile, HTTPException
from ..core.config import settings

@dataclass
class ValidatedImage:
    image: Image.Image
    filename: str
    size_bytes: int
    dimensions: Tuple[int, int]
    format: str

class ImageService:
    @staticmethod
    async def validate_and_process(file: UploadFile) -> ValidatedImage:
        """
        Validates uploaded image file:
        - Rejects files larger than MAX_UPLOAD_SIZE_BYTES (10 MB).
        - Rejects unsupported extensions (.jpg, .jpeg, .png).
        - Detects empty and corrupted image streams.
        - Converts color profile to RGB.
        - Extracts natural image dimensions.
        - Keeps data purely in-memory (no permanent disk writes).
        """
        if not file or not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file was provided in the upload request."
            )

        # 1. Extension Check
        extension = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '.{extension}'. Only JPG, JPEG, and PNG retinal photographs are accepted."
            )

        # 2. Read Stream & Check Size
        try:
            content = await file.read()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to read uploaded file: {str(e)}"
            )

        size_bytes = len(content)
        if size_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty (0 bytes). Please provide a valid retinal photograph."
            )

        if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
            size_mb = size_bytes / (1024 * 1024)
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File size ({size_mb:.2f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB."
            )

        # 3. Decode with Pillow & Verify Integrity
        try:
            img = Image.open(io.BytesIO(content))
            # Force raster load to verify image data integrity and catch truncation/corruption
            img.load()
        except (UnidentifiedImageError, OSError, SyntaxError) as e:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is corrupted or could not be decoded as an image."
            )

        # 4. Check Decoded Format
        detected_format = img.format or "UNKNOWN"
        if detected_format.upper() not in ("JPEG", "PNG"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image encoding '{detected_format}'. Only standard JPEG and PNG files are accepted."
            )

        width, height = img.size
        if width <= 0 or height <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid image dimensions detected."
            )

        # 5. Convert to RGB if needed (strips Alpha channels, handles Grayscale/CMYK)
        if img.mode != "RGB":
            try:
                img = img.convert("RGB")
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to convert image color space to RGB: {str(e)}"
                )

        return ValidatedImage(
            image=img,
            filename=file.filename,
            size_bytes=size_bytes,
            dimensions=(width, height),
            format=detected_format.upper()
        )

image_service = ImageService()

