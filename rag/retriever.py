import numpy as np
from rag.vector_store.faiss_store import load_faiss_index
from rag.embedding.embedder import Embedder

TOP_K = 10
EMBED_MODEL = "text-embedding-3-small"

def embed_query(query, model_name=EMBED_MODEL):
    """
    Вернуть вектор запроса (np.float32).
    Здесь embedder.embed_batch возвращает list[vector], берем первый элемент.
    """
    embedder = Embedder(model_name=model_name)
    vec = embedder.embed_batch([query], batch_size=1)[0]
    return np.array(vec, dtype="float32")

def search(query, top_k=TOP_K):
    """
    Поиск top_k кандидатов по FAISS.
    Возвращает список метаданных (metadata entries) с расстояниями.
    """
    # 1) загружаем индекс и metadata
    index, metadata = load_faiss_index()

    # 2) получаем вектор запроса
    q_vec = embed_query(query)
    q_vec = q_vec.reshape(1, -1)

    # 3) делаем поиск
    distances, indices = index.search(q_vec, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        # idx — позиция вектора в индексе (0..N-1)
        # metadata — список словарей в том же порядке, что и векторы
        if idx < 0:
            continue
        meta = metadata[idx]
        results.append({"score": float(dist), "meta": meta})

    return results

if __name__ == "__main__":
    while True:
        q = input("\nQuery (or 'exit')> ").strip()
        if q.lower() in ("exit", "quit"):
            break
        res = search(q, top_k=5)
        print(f"Found {len(res)} results:")
        for i, r in enumerate(res, 1):
            m = r["meta"]
            print(f"{i}. {m.get('full_name','<no name>')} — {m.get('professional_title','')} — score={r['score']:.4f}")
            print("   summary:", m.get("summary_generated","")[:200])
