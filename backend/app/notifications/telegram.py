import logging

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, message: str) -> None:
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            logger.info("Telegram not configured; skipped alert: %s", message)
            return
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    url,
                    json={"chat_id": self.settings.telegram_chat_id, "text": message},
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Telegram alert failed: %s", exc)
