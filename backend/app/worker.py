import asyncio
import logging

from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Worker started. Add scheduled strategy scans and reconciliation jobs here.")
    while True:
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
