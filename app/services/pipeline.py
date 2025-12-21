import logging
from app.services.onboarding import CandidateInput
from rag.agents.summary_agent import SummaryAgent
from rag.embedding.embedder import Embedder

summary_agent = SummaryAgent()
embedder = Embedder()
logger = logging.getLogger("pipeline")


def _prepare_candidate_data_dict(data: CandidateInput) -> dict:
    """
    Converts CandidateInput Pydantic model to dict for SummaryAgent.
    SummaryAgent now handles both dict and raw text formats.
    """
    return {
        "full_name": data.full_name,
        "professional_title": data.professional_title or "",
        "years_experience": data.years_experience or 0,
        "skills": str(data.skills) if data.skills else "",
        "location": data.location or "",
        "projects": str(data.projects) if data.projects else "",
        "work_history": str(data.work_history) if data.work_history else "",
        "education": data.education or "",
        "certifications": str(data.certifications) if data.certifications else "",
        "spoken_languages": str(data.spoken_languages) if data.spoken_languages else "",
    }


def _prepare_text_for_embedding(data: CandidateInput, summary: str) -> str:
    """
    Formats the text string for vector generation.
    Includes the generated summary as it contains the condensed essence of the candidate's profile.
    """
    parts = [
        data.professional_title,
        str(data.skills),
        str(data.years_experience),
        summary,
        str(data.spoken_languages),
        data.location,
    ]
    return " | ".join([str(p) for p in parts if p])


async def process_candidate_background(
    candidate_id: str, data: CandidateInput, db_pool
):
    """
    Background task to process a new candidate:
    1. Generates a descriptive Summary (using GPT).
    2. Generates the Vector Embedding (using OpenAI).
    3. Updates the candidate record in PostgreSQL with the Summary and Vector.
    """
    logger.info(f"Starting background processing for {candidate_id}")

    try:
        # Convert CandidateInput to dict for unified SummaryAgent
        candidate_dict = _prepare_candidate_data_dict(data)
        summary = summary_agent.generate_summary(candidate_dict)

        text_for_embed = _prepare_text_for_embedding(data, summary)
        vector_list = embedder.embed_batch([text_for_embed])[0]

        vector_str = str(vector_list)

        update_query = """
                       UPDATE candidates
                       SET summary_generated = $1,
                           embedding         = $2::vector,
                           updated_at        = NOW()
                       WHERE id = $3
                       """

        async with db_pool.acquire() as conn:
            await conn.execute(update_query, summary, vector_str, candidate_id)

        logger.info(f"Successfully processed candidate {candidate_id}")

    except Exception as e:
        logger.error(f"Error processing candidate {candidate_id}: {e}", exc_info=True)
