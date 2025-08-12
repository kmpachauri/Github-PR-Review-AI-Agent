from pydantic import BaseModel
from typing import Optional

class PRRequest(BaseModel):
    repo_url: str
    pr_number: int
    github_token: Optional[str] = None
