""" OVERVIEW:
FASTAPI stuff
"""
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.service.url_recipe_extractor import (
    ExtractionErrorType,
    RecipeExtractionError,
    extract_recipe_from_url,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Recipe AI Service")

ERROR_STATUS_MAP = {
    ExtractionErrorType.BLOCKED: 502,
    ExtractionErrorType.NOT_FOUND: 404,
    ExtractionErrorType.UNREACHABLE: 502,
    ExtractionErrorType.TIMEOUT: 504,
    ExtractionErrorType.HTTP_ERROR: 502,
    ExtractionErrorType.NO_RECIPE_DATA: 422,
}


class RecipeUrlRequest(BaseModel):
    url: str


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/extract/url")
def extract_url(request: RecipeUrlRequest):
    logger.info(f"Extracting recipe from URL: {request.url}")
    try:
        return extract_recipe_from_url(request.url)
    except RecipeExtractionError as e:
        logger.warning(f"Extraction failed ({e.error_type.value}): {e.message}")
        raise HTTPException(status_code=ERROR_STATUS_MAP[e.error_type], detail=e.message) from e
