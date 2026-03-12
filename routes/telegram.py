"""FinanzBro - Telegram Webhook Route.

Empfängt eingehende Nachrichten von Telegram via Webhook
und leitet sie an den Command Handler weiter.
"""
import logging

from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["telegram"])

logger = logging.getLogger(__name__)


@router.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    """Empfängt Telegram-Updates via Webhook.

    Telegram sendet POST-Requests mit Update-JSON hierhin.
    Der Webhook wird beim App-Start automatisch registriert.
    """
    try:
        update = await request.json()
        logger.debug(f"Telegram-Update empfangen: {update.get('update_id', '?')}")

        # Asynchron verarbeiten (Telegram erwartet schnelle 200-Antwort)
        from services.telegram_bot import handle_update
        import asyncio
        asyncio.create_task(handle_update(update))

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Telegram-Webhook-Fehler: {e}")
        return Response(status_code=200)  # Immer 200 zurückgeben, sonst retried Telegram
