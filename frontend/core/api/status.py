from core.api.base import BaseApi


class StatusApi(BaseApi):
    def check(self) -> dict:
        # envelope=False: SettingsController сам разбирает {"success", "data"},
        # чтобы отличать "бекенд ответил, но degraded" от "бекенд недоступен"
        return self.get("/api/status", envelope=False)
