from core.api.base import BaseApi

class BranchApi(BaseApi):
    def get_all(self):
        return self.get("/api/branches")
