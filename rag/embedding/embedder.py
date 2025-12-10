import os
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

class Embedder:
    def __init__(self, model_name="text-embedding-3-small"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_name = model_name

    def embed_batch(self, texts, batch_size=32):
        """Embedding a list of texts in batches."""
        vectors = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self.client.embeddings.create(
                model=self.model_name,
                input=batch
            )
            vecs = [item.embedding for item in response.data]
            vectors.extend(vecs)
        return vectors