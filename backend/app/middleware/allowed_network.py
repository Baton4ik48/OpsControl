from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import ipaddress


class AllowedNetworkMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_networks: list[str]):
        super().__init__(app)
        self.allowed_networks = [ipaddress.ip_network(net) for net in allowed_networks]

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host

        ip = ipaddress.ip_address(client_ip)

        allowed = any(ip in network for network in self.allowed_networks)

        if not allowed:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied from this network",
                    "client_ip": client_ip,
                },
            )

        return await call_next(request)
