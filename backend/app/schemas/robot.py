from datetime import datetime

from pydantic import BaseModel

STAGES = ("queued", "driving", "picking", "returning", "arrived")
FAILURES = ("missing", "blocked", "fault")


class RobotJobResponse(BaseModel):
    """The robot's current job, or an idle marker when there is none."""

    active: bool
    stage: str | None = None
    stage_index: int = -1
    shelf_number: int | None = None
    item: str | None = None
    elapsed_seconds: float = 0.0
    failure: str | None = None
    simulated: bool = True


class HistoryEntry(BaseModel):
    id: str
    user_input: str
    item: str | None
    shelf_number: int | None
    succeeded: bool
    failure: str | None
    created_at: datetime


class HistoryResponse(BaseModel):
    entries: list[HistoryEntry]
