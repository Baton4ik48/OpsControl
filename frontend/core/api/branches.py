from core.api.base import BaseApi

class BranchApi(BaseApi):

    def get_all(self):
        return self.get("/api/branches")

    def create(self, name: str):
        return self.post(
            "/api/branches",
            json={
                "name": name
            }
        )

    def update_branch(self, branch_id: int, name: str):
        return self.put(
            f"/api/branches/{branch_id}",
            json={
                "name": name
            }
        )

    def delete_branch(self, branch_id: int):
        return self.delete(f"/api/branches/{branch_id}")