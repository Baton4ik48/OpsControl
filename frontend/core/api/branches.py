from core.api.base import BaseApi

class BranchApi(BaseApi):
    def get_all(self):
        return self.get("/api/branches")
    
    def create(self, name: str):
        return self.post("/api/branches", params={"name": name})

    def delete_branch(self, branch_id: int):
        return super().delete(f"/api/branches/{branch_id}")
    def update_branch(self, branch_id: int, new_name: str):
        return self.put(
            f"/api/branches/{branch_id}",
            params={"new_name": new_name}
        )