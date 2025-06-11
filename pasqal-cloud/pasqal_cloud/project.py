from pydantic import BaseModel, ConfigDict


class Project(BaseModel):
    id: str
    name: str

    model_config = ConfigDict(extra="allow")
