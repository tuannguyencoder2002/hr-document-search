"""Application configuration loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration. Values can be overridden via environment / .env."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_mode: str = "local"  # "local" (embedded, no Docker) | "remote" (needs Qdrant server)
    qdrant_local_path: str = ""  # auto-set to PROJECT_ROOT/qdrant_data if empty
    qdrant_collection: str = "hr_documents"
    qdrant_dense_name: str = "dense"
    qdrant_sparse_name: str = "sparse"
    qdrant_dense_size: int = 1024

    # Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_keep_alive: str = "30m"  # keep model resident in VRAM between requests
    ollama_num_gpu: int = -1        # -1 = offload all layers to GPU

    # Models
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 128

    # Search
    top_k_retrieve: int = 30
    top_k_rerank: int = 5
    rrf_k: int = 60
    rerank_min_score: float = 0.55  # below this, consider "not found"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # LLM generation
    llm_temperature: float = 0.2
    llm_top_p: float = 0.9
    llm_max_tokens: int = 512

    # Data
    data_dir: Path = Field(default=PROJECT_ROOT / "data" / "corpus")

    # Device
    device: str = "auto"  # "auto" | "cuda" | "cpu"

    # Image search (CLIP)
    image_search_enabled: bool = True
    clip_text_model: str = "sentence-transformers/clip-ViT-B-32-multilingual-v1"
    clip_image_model: str = "sentence-transformers/clip-ViT-B-32"
    clip_vector_size: int = 512
    image_collection: str = "hr_images"
    image_store_dir: Path = Field(default=PROJECT_ROOT / "data" / "extracted_images")
    image_min_width: int = 80   # skip tiny images (icons, bullets)
    image_min_height: int = 80
    image_top_k: int = 3

    def resolved_device(self) -> str:
        if self.device != "auto":
            return self.device
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def resolved_qdrant_local_path(self) -> str:
        if self.qdrant_local_path:
            return self.qdrant_local_path
        return str(PROJECT_ROOT / "qdrant_data")

    def create_qdrant_client(self):
        """Factory: return QdrantClient based on qdrant_mode."""
        from qdrant_client import QdrantClient

        if self.qdrant_mode == "local":
            path = self.resolved_qdrant_local_path()
            return QdrantClient(path=path)
        return QdrantClient(url=self.qdrant_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor for settings."""
    return Settings()
