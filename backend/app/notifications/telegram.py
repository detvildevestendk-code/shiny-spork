import logging
from typing import Any

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

    async def alert(self, level: str, event: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        icon = {
            "info": "INFO",
            "warning": "WARNING",
            "error": "ERROR",
            "trade": "TRADE",
            "signal": "SIGNAL",
            "startup": "STARTUP",
            "shutdown": "SHUTDOWN",
        }.get(level.lower(), level.upper())
        lines = [f"[{icon}] {event}", message]
        if metadata:
            for key, value in metadata.items():
                if value is not None:
                    lines.append(f"{key}: {value}")
        await self.send("\n".join(lines))

    async def startup(self, service: str, metadata: dict[str, Any] | None = None) -> None:
        await self.alert("startup", f"{service} startup", "Service started", metadata)

    async def shutdown(self, service: str, metadata: dict[str, Any] | None = None) -> None:
        await self.alert("shutdown", f"{service} shutdown", "Service stopped", metadata)

    async def error(self, event: str, exc: Exception | str, metadata: dict[str, Any] | None = None) -> None:
        message = str(exc)
        if isinstance(exc, Exception):
            message = f"{type(exc).__name__}: {exc}"
        await self.alert("error", event, message, metadata)

    async def warning(self, event: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        await self.alert("warning", event, message, metadata)

    async def strategy_signal(
        self,
        strategy_name: str,
        symbol: str,
        action: str,
        confidence: float | None,
        reason: str | None = None,
    ) -> None:
        await self.alert(
            "signal",
            "Strategy signal",
            reason or "Strategy generated a signal",
            {
                "strategy": strategy_name,
                "symbol": symbol,
                "action": action,
                "confidence": confidence,
            },
        )

    async def simulated_trade(
        self,
        event: str,
        symbol: str,
        side: str,
        amount: float | None = None,
        price: float | None = None,
        pnl: float | None = None,
        reason: str | None = None,
    ) -> None:
        await self.alert(
            "trade",
            event,
            reason or "Paper trade event",
            {
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "pnl": pnl,
            },
        )

    async def worker_crash(self, exc: Exception, metadata: dict[str, Any] | None = None) -> None:
        await self.error("Worker crash", exc, metadata)
