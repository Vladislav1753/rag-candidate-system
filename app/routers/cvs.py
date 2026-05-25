import logging

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Request,
    UploadFile,
)

from app.middleware.rate_limit import (
    RATE_LIMIT_EXTRACT,
    limiter,
)
from app.services.parser import extract_text_from_pdf
from rag.onboarding_graph import app_workflow

logger = logging.getLogger(__name__)

cvs_router = APIRouter(prefix="/cvs", tags=["cvs"])


@cvs_router.post("/extract")
@limiter.limit(RATE_LIMIT_EXTRACT)
async def extract_from_pdf(request: Request, file: UploadFile = File(...)):
    logger.info(f"Receiving file: {file.filename}")

    try:
        raw_text = extract_text_from_pdf(file.file)
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid PDF file") from e

    if not raw_text or len(raw_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="PDF text is too short or empty.")

    try:
        result = app_workflow.invoke({"raw_text": raw_text})

        return {
            "status": "success",
            "extracted_data": result.get("extracted_data", {}),
            "final_summary": result.get("final_summary", ""),
        }
    except Exception as e:
        logger.error(f"Extraction workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
