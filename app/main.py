from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import logging

from app.services.onboarding import (
    CandidateOnboardingService,
    CandidateInput,
    init_db_pool,
)
from app.services.pipeline import process_candidate_background
from app.services.parser import extract_text_from_pdf
from rag.retriever import search_candidates
from rag.reranker import RerankerService
from rag.onboarding_graph import app_workflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")

db_pool = None
reranker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, reranker
    logger.info("Connecting to Database...")
    db_pool = await init_db_pool()

    logger.info("Loading Reranker model (CrossEncoder)...")
    reranker = RerankerService()

    yield
    if db_pool:
        logger.info("Closing Database connection...")
        await db_pool.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    min_experience: Optional[int] = None
    top_k: int = 5


@app.post("/extract")
async def extract_from_pdf(file: UploadFile = File(...)):
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


@app.post("/onboarding")
async def onboard_candidate(data: CandidateInput, background_tasks: BackgroundTasks):
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")

    service = CandidateOnboardingService(db_pool)
    result = await service.create_candidate(data)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))

    candidate_id = result["candidate_id"]

    background_tasks.add_task(process_candidate_background, candidate_id, data, db_pool)

    return {"status": "processing", "candidate_id": candidate_id}


@app.post("/search")
async def search_endpoint(req: SearchRequest):
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")

    if not reranker:
        raise HTTPException(status_code=500, detail="Reranker not initialized")

    filters = {}
    if req.location:
        filters["location"] = req.location
    if req.min_experience:
        filters["min_experience"] = req.min_experience

    candidates = await search_candidates(
        query=req.query, filters=filters, db_pool=db_pool, top_k=req.top_k
    )

    logger.info(f"Database found {len(candidates)} candidates. Query: '{req.query}'")

    if not candidates:
        return {"results": []}

    if req.query:
        try:
            ranked_results = reranker.rank_candidates(
                query=req.query, candidates=candidates, top_k=req.top_k
            )
            logger.info(f"Reranking complete. Returning {len(ranked_results)} results.")
            return {"results": ranked_results}
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            return {"results": candidates[: req.top_k]}
    return {"results": candidates[: req.top_k]}
