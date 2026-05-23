from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary() -> dict:
    return {
        "live_pnl": 0,
        "open_positions": [],
        "risk_exposure_pct": 0,
        "ai_confidence_score": None,
        "exchange_connection_status": "not_checked",
        "strategy_toggles": {
            "ema_crossover": True,
            "rsi_divergence": True,
            "volume_breakout": False,
            "trend_following": False,
            "mean_reversion": False,
            "scalping_mode": False,
        },
        "telegram_alerts_enabled": False,
    }


@router.get("/trades")
async def trade_history() -> dict:
    return {"items": [], "total": 0}
