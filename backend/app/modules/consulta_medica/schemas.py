from pydantic import BaseModel


class SymptomOut(BaseModel):
    code: str
    term: str


class SymptomSearchOut(BaseModel):
    items: list[SymptomOut]
    page: int
    has_more: bool
