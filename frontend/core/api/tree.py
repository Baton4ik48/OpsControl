from core.api.base import BaseApi

class TreeApi(BaseApi):
    def load_tree(self):
        return self.get("/api/tree")

