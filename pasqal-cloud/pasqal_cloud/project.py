from pydantic import BaseModel


class Project(BaseModel):
    id: str
    name: str
