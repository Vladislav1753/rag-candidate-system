import logging
from app.services.onboarding import CandidateInput
from rag.agents.summary_agent import SummaryAgent
from rag.embedding.embedder import Embedder

summary_agent = SummaryAgent()
embedder = Embedder()
logger = logging.getLogger("pipeline")


def _prepare_text_for_summary(data: CandidateInput) -> str:
    """Formats the candidate data into a string for the LLM to generate a summary."""
    return f"""
    Name: {data.full_name}
    Title: {data.professional_title}
    Experience: {data.years_experience} years
    Skills: {data.skills}
    Work History: {data.work_history}
    Projects: {data.projects}
    Location: {data.location}
    Spoken Languages: {data.spoken_languages}
    Education: {data.education}
    Certifications: {data.certifications}
    """


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
        text_for_summary = _prepare_text_for_summary(data)
        summary = summary_agent.generate_summary(text_for_summary)

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
