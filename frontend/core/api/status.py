from core.api.base import BaseApi


class StatusApi(BaseApi):
    def check(self) -> dict:
        return self.get("/api/status")
