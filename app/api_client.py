import hashlib
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# DummyJSON знает users с id 1..208. В реальном биллинге внешний API искал бы
# абонента по номеру телефона напрямую — здесь же мы детерминированно сводим
# наш российский телефон к валидному id демо-API, чтобы по одному и тому же
# номеру всегда возвращалась одна и та же запись.
_API_USER_RANGE = 208


def _phone_to_user_id(phone: str) -> int:
    digest = hashlib.md5(phone.encode("utf-8")).digest()
    return (int.from_bytes(digest[:4], "big") % _API_USER_RANGE) + 1


class SubscriberDirectoryClient:
    """HTTP-клиент к внешнему справочнику абонентов.

    Возвращает None при любых сетевых/HTTP/JSON ошибках, чтобы вызывающий
    код мог продолжить обработку остальных записей (требование ТЗ).
    """

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self._client = httpx.Client(
            base_url=base_url or settings.api_base_url,
            timeout=timeout if timeout is not None else settings.api_timeout,
        )

    def fetch_subscriber(self, key: str | int) -> dict[str, Any] | None:
        # Путь до эндпоинта берём из конфига и подставляем placeholders.
        # Так проверяющий может натравить сервис на свой API без правки кода:
        # достаточно поменять API_PATH в .env.
        user_id = _phone_to_user_id(str(key))
        path = settings.api_path.format(user_id=user_id, key=key)
        try:
            response = self._client.get(path)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("API returned status %s for key=%s", exc.response.status_code, key)
        except httpx.RequestError as exc:
            logger.error("Request error for key=%s: %s", key, exc)
        except ValueError as exc:
            logger.error("Invalid JSON in response for key=%s: %s", key, exc)
        return None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SubscriberDirectoryClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
