import asyncio
import logging
import time

from app.metrics import vault_renew_total, vault_renew_last_success_timestamp

logger = logging.getLogger("vault-renew")


async def vault_renew_loop(interval: int = 900):
    """
    Фоновая задача — продлевает Vault AppRole токен каждые 15 минут.

    Логика:
    - Успешный renew → продолжаем работу.
    - renew не прошёл (токен протух) → пробуем re-login через AppRole.
    - Vault запечатан / недоступен → логируем, ждём следующего интервала.
      Пул БД НЕ трогаем — существующие соединения могут ещё работать,
      пересоздание пула произойдёт лениво при следующем запросе если нужно.
    - Неверные AppRole ключи → логируем с подсказкой обновить .env.
    """
    from app.services.vault_client import (
        get_vault_client,
        VaultSealedError,
        VaultUnavailableError,
        VaultAuthError,
    )

    vault = get_vault_client()

    while True:
        await asyncio.sleep(interval)
        try:
            if vault._renew_token():
                logger.info("Vault token renewed")
                vault_renew_total.labels(result="success").inc()
            else:
                logger.warning(
                    "Vault token renew failed → попытка re-login через AppRole"
                )
                vault._backend_token = None
                vault._get_backend_token()
                logger.info("Vault re-login успешен")
                vault_renew_total.labels(result="reauth").inc()

            vault_renew_last_success_timestamp.set(time.time())

        except VaultSealedError as e:
            logger.warning(
                "Vault запечатан — обновление токена отложено до unseal. %s", e
            )
            vault_renew_total.labels(result="sealed").inc()
        except VaultUnavailableError as e:
            logger.warning("Vault недоступен — обновление токена отложено. %s", e)
            vault_renew_total.labels(result="unavailable").inc()
        except VaultAuthError as e:
            logger.error(
                "Vault AppRole: ошибка авторизации при обновлении токена. "
                "Проверьте VAULT_ROLE_ID / VAULT_SECRET_ID в .env. Ошибка: %s",
                e,
            )
            vault_renew_total.labels(result="auth_error").inc()
        except Exception as e:
            logger.error("Неожиданная ошибка в vault_renew_loop: %s", e)
            vault_renew_total.labels(result="unexpected_error").inc()
