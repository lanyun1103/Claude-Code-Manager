from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    git_url: str | None = None
    default_branch: str = "main"


class ProjectUpdate(BaseModel):
    name: str | None = None
    git_url: str | None = None
    has_remote: bool | None = None
    default_branch: str | None = None
    show_in_selector: bool | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    git_url: str | None
    has_remote: bool
    local_path: str | None
    default_branch: str
    status: str
    error_message: str | None
    show_in_selector: bool
    created_at: datetime

    model_config = {"from_attributes": True}
