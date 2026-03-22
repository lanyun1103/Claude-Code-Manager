from pydantic import BaseModel


class TagCreate(BaseModel):
    name: str
    color: str = "indigo"


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class TagResponse(BaseModel):
    id: int
    name: str
    color: str
    created_at: str

    model_config = {"from_attributes": True}
