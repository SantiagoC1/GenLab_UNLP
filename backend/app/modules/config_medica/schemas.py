from pydantic import BaseModel


class SymptomData(BaseModel):
    code: str | None = None
    term: str | None = None


class PathologyData(BaseModel):
    name: str | None = None
    cardinal: SymptomData | None = None
    secondary: list[SymptomData] | None = None


class PathologySymptomsData(BaseModel):
    cardinal: SymptomData | None = None
    secondary: list[SymptomData] | None = None


class CdssStrategyData(BaseModel):
    strategy: str | None = None


class SymptomOut(BaseModel):
    code: str
    term: str


class PathologyOut(BaseModel):
    id: int
    name: str
    cardinal: SymptomOut | None
    secondary: list[SymptomOut]


class CdssStrategyOut(BaseModel):
    strategy: str
