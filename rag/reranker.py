import logging
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

logger = logging.getLogger("reranker")


class RerankerService:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        logger.info(f"Loading CrossEncoder model: {model_name}...")
        self.model = CrossEncoder(model_name)
        logger.info("CrossEncoder model loaded successfully.")

    def _format_list_field(self, data: Any) -> str:
        """Helper to convert lists (like skills/tools) into comma-separated strings."""
        if isinstance(data, list):
            return ", ".join([str(item) for item in data])
        if isinstance(data, dict) and "manual_list" in data:
            return ", ".join(data["manual_list"])
        return str(data) if data else ""

    def _format_complex_list(self, data: List[Dict], fields: List[str]) -> str:
        """
        Helper to extract specific fields from a list of dicts (e.g. Projects, Work History).
        Example: extracts 'name' and 'description' from projects.
        """
        if not data or not isinstance(data, list):
            return ""

        items = []
        for item in data:
            parts = [str(item.get(f, "")).strip() for f in fields if item.get(f)]
            if parts:
                items.append(" - ".join(parts))

        return "; ".join(items)

    def rank_candidates(
        self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        pairs = []
        for cand in candidates:
            work_hist_str = self._format_complex_list(
                cand.get("work_history", []),
                fields=["position", "company", "description"],
            )

            projects_str = self._format_complex_list(
                cand.get("projects", []), fields=["name", "description"]
            )

            skills_str = self._format_list_field(cand.get("skills", ""))
            tools_str = self._format_list_field(cand.get("tools", ""))

            langs = cand.get("languages", [])
            langs_str = (
                ", ".join(langs) if isinstance(langs, list) else str(langs or "")
            )

            education_str = cand.get("education") or ""
            certs_str = cand.get("certifications") or ""

            parts = [
                f"Title: {cand.get('professional_title') or 'Unknown'}",
                f"Experience: {cand.get('years_experience') or 0} years",
                f"Location: {cand.get('location') or 'Unknown'}",
                f"Languages: {langs_str}",
                f"Education: {education_str}",
                f"Certifications: {certs_str}",
                f"Skills: {skills_str}",
                f"Tools: {tools_str}",
                f"Work History: {work_hist_str}",
                f"Projects: {projects_str}",
                f"Summary: {cand.get('summary') or ''}",
            ]

            candidate_text = ". ".join([p for p in parts if len(p) > 15])

            pairs.append([query, candidate_text])

        logger.info(f"Re-ranking {len(candidates)} candidates for query: '{query}'")

        if not pairs:
            return candidates[:top_k]

        scores = self.model.predict(pairs)

        scored_candidates = []
        for cand, score in zip(candidates, scores):
            cand["rerank_score"] = float(score)
            scored_candidates.append(cand)

        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored_candidates[:top_k]
