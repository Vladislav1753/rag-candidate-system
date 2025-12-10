import faiss
import numpy as np
import pickle
import os

INDEX_PATH = "data/faiss_index.bin"
META_PATH = "data/candidates_meta.pkl"

def save_faiss_index(vectors, metadata):
    vectors = np.array(vectors).astype("float32")
    dimension = vectors.shape[1]

    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)

    faiss.write_index(index, INDEX_PATH)

    with open(META_PATH, "wb") as f:
        pickle.dump(metadata, f)

    print(f"FAISS index saved: {INDEX_PATH}")
    print(f"Metadata saved: {META_PATH}")


def load_faiss_index():
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError("FAISS index not found")

    index = faiss.read_index(INDEX_PATH)

    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)

    return index, metadata