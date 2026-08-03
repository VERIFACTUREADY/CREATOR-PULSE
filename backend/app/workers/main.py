"""Punto de entrada del worker RQ.

Uso:
    python -m app.workers.main
"""

from __future__ import annotations

import sys

from rq import Worker

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import check_database, detect_pgvector
from app.workers.queue import get_queue, get_redis

logger = get_logger(__name__)


def main() -> int:
    configure_logging(settings.log_level, settings.log_json)

    if not check_database():
        logger.error("worker_database_unavailable", url_host=settings.database_url.split("@")[-1])
        return 1

    pgvector = detect_pgvector()
    logger.info(
        "worker_starting",
        queue=settings.rq_queue_name,
        pgvector=pgvector,
        embedding_backend=settings.embedding_backend,
        sentiment_backend=settings.sentiment_backend,
        ai_provider=settings.ai_provider,
    )

    worker = Worker([get_queue()], connection=get_redis())
    worker.work(with_scheduler=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
