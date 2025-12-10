import pandas as pd
from rag.embedding.embedder import Embedder
from rag.vector_store.faiss_store import save_faiss_index

CSV_PATH = "data/candidates_pool.csv"

def prepare_text(row):
    parts = [
        row["professional_title"],
        row["skills"],
        row["years_experience"],
        row["summary_generated"],
        row["spoken_languages"],
        row["location"]
    ]
    parts = [str(p) for p in parts if pd.notna(p)]
    return " | ".join(parts)


def main():
    data = pd.read_csv(CSV_PATH)

    texts = [prepare_text(row) for _, row in data.iterrows()]

    embedder = Embedder()
    vectors = embedder.embed_batch(texts)

    metadata = data.to_dict(orient="records")

    save_faiss_index(vectors, metadata)


if __name__ == "__main__":
    main()
