import asyncio
import logging

logger = logging.getLogger("vault-renew")


async def vault_renew_loop(interval: int = 900):
    """
    Фоновая задача — продлевает Vault токен каждые 15 минут.
    Если renew не прошёл — проактивно пересоздаём пул.
    """
    from app.services.vault_client import get_vault_client
    from app.services.db.pool import close_pool, init_pool

    vault = get_vault_client()

    while True:
        await asyncio.sleep(interval)
        try:
            if vault._renew_token():
                logger.info("Vault token renewed successfully")
            else:
                logger.warning("Vault token renew failed, recreating pool proactively")
                close_pool()
                init_pool()
        except Exception as e:
            logger.warning(f"Vault token renew failed: {e}")
            close_pool()
            init_pool()