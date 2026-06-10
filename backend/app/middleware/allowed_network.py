import ipaddress
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("allowed_network")


class AllowedNetworkMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        allowed_networks: list[str],
        trusted_proxies: list[str] | None = None,
    ):
        super().__init__(app)
        self.allowed_networks = [ipaddress.ip_network(net) for net in allowed_networks]
        # strict=False разрешает адреса хостов типа "172.18.0.5" вместе с CIDR
        self.trusted_proxies = [
            ipaddress.ip_network(p, strict=False) for p in (trusted_proxies or [])
        ]

    def _normalize(
        self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address
    ) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        """Разворачивает IPv4-mapped IPv6 адреса (::ffff:x.x.x.x → x.x.x.x)."""
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            return ip.ipv4_mapped
        return ip

    def _is_trusted_proxy(
        self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address
    ) -> bool:
        return any(ip in net for net in self.trusted_proxies)

    def _resolve_client_ip(self, request: Request) -> str:
        """
        Возвращает эффективный IP клиента.

        Если прямое соединение пришло от доверенного прокси, читает реальный IP
        из заголовка X-Real-IP (выставляется nginx как $remote_addr —
        клиент не может его подделать). Иначе использует сырой адрес TCP-соединения.

        X-Forwarded-For намеренно не используется: его крайнее левое значение
        полностью контролируется клиентом и тривиально подделывается.
        """
        connection_host = request.client.host

        try:
            conn_ip = self._normalize(ipaddress.ip_address(connection_host))
        except ValueError:
            return connection_host

        if self._is_trusted_proxy(conn_ip):
            real_ip = request.headers.get("X-Real-IP", "").strip()
            if real_ip:
                try:
                    ipaddress.ip_address(real_ip)  # валидация перед использованием
                    return real_ip
                except ValueError:
                    logger.warning(
                        "Trusted proxy %s sent invalid X-Real-IP %r — using connection host",
                        connection_host,
                        real_ip,
                    )

        return connection_host

    async def dispatch(self, request: Request, call_next):
        client_ip = self._resolve_client_ip(request)

        try:
            ip = self._normalize(ipaddress.ip_address(client_ip))
        except ValueError:
            logger.warning("Unparseable client IP %r — denying", client_ip)
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied from this network",
                    "client_ip": client_ip,
                },
            )

        allowed = any(ip in network for network in self.allowed_networks)

        if not allowed:
            logger.warning(
                "Access denied from %s — not in allowed_networks",
                client_ip,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied from this network",
                    "client_ip": client_ip,
                },
            )

        # Сохраняем определённый IP, чтобы downstream middleware и обработчики могли его читать
        request.state.client_ip = client_ip

        return await call_next(request)
