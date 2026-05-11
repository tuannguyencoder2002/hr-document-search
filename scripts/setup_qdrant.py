"""Create the Qdrant collection with dense + sparse vector configs."""

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
    ensure_collection(client, settings.qdrant_collection, settings.qdrant_dense_size)
    info = client.get_collection(settings.qdrant_collection)
    logger.info("Collection '%s' ready. Points count: %s", settings.qdrant_collection, info.points_count)


if __name__ == "__main__":
    main()
