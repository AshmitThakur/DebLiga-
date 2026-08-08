from pydantic import BaseModel


class PoolCreate(BaseModel):
    name: str


class TeamCreate(BaseModel):
    name: str
    pool_id: int


class SpeakerCreate(BaseModel):
    name: str
    team_id: int


class RoundCreate(BaseModel):
    number: int
    motion: str | None = None


class DebateCreate(BaseModel):
    round_id: int
    team1_id: int
    team2_id: int
    room: str | None = None
    stage: str = "pool"


class PerformanceInput(BaseModel):
    speaker_id: int
    role: str
    score: float


class ResultCreate(BaseModel):
    winner_team_id: int
    performances: list[PerformanceInput]

class TeamUpdate(BaseModel):
    name: str
    pool_id: int


class SpeakerUpdate(BaseModel):
    name: str
    team_id: int

class PoolUpdate(BaseModel):
    name: str


class RoundUpdate(BaseModel):
    number: int
    motion: str | None = None


class DebateUpdate(BaseModel):
    round_id: int
    team1_id: int
    team2_id: int
    room: str | None = None
    stage: str = "pool"

class DebateCreate(BaseModel):
    round_id: int
    team1_id: int
    team2_id: int
    room: str | None = None
    stage: str = "pool"


class PoolUpdate(BaseModel):
    name: str


class RoundUpdate(BaseModel):
    number: int
    motion: str | None = None


class DebateUpdate(BaseModel):
    round_id: int
    team1_id: int
    team2_id: int
    room: str | None = None
    stage: str = "pool"