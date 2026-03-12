from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    min_score: float = float(os.getenv("RAG_MIN_SCORE", "0.2"))
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "demo_products")
    embedding_dim: int = int(os.getenv("RAG_EMBEDDING_DIM", "96"))


settings = Settings()
