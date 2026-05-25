from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str | None = None
    location: str | None = None
    min_experience: int | None = None
    top_k: int = 5
