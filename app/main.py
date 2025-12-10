from fastapi import FastAPI
from pydantic import BaseModel
from rag.retriever import search

app = FastAPI()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@app.post("/search")
def search_candidates(req: SearchRequest):
    results = search(req.query, top_k=req.top_k)
    return {"results": results}