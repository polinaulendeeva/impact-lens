from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384 dimensions, runs on a laptop CPU
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL_NAME)


def embed_passages(texts):
    return get_model().encode(
        texts, batch_size=32, normalize_embeddings=True, show_progress_bar=True
    ).tolist()


def embed_query(text):
    return get_model().encode(QUERY_PREFIX + text, normalize_embeddings=True).tolist()
