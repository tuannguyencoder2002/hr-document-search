"""Drop and recreate the Qdrant collection."""

from __future__ import annotations

from qdrant_client import QdrantClient

from src.config import get_settings
from src.ingestion.indexer import ensure_collection
from src.utils.logger import get_logger, setup_logging


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    settings = get_settings()
    client = settings.create_qdrant_client()
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection in existing:
        client.delete_collection(settings.qdrant_collection)
        logger.warning("Deleted collection '%s'", settings.qdrant_collection)
    ensure_collection(client, settings.qdrant_collection, settings.qdrant_dense_size)
    logger.info("Recreated collection '%s'", settings.qdrant_collection)


if __name__ == "__main__":
    main()
