from pydantic import BaseModel, Field
from typing import Optional

class PRRequest(BaseModel):
    repo_url: str = Field(default="https://github.com/", description="GitHub repo URL")
    pr_number: int = Field(..., description="Pull request number")
    github_token: Optional[str] = Field(default=None, description="GitHub token")
