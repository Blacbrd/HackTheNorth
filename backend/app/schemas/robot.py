from datetime import datetime

from pydantic import BaseModel

SINGLE_STAGES = ("picking", "driving", "arrived")
FAILURES = ("missing", "blocked", "fault")


class RobotJobItem(BaseModel):
    shelf_number: int
    item: str


class RobotJobResponse(BaseModel):
    """The robot's current job, or an idle marker when there is none."""

    active: bool
    stage: str | None = None
    stage_index: int = -1
    stages: list[str] = []
    # First item, kept for back-compat with clients that only ever knew about
    # a single item.
    shelf_number: int | None = None
    item: str | None = None
    items: list[RobotJobItem] = []
    elapsed_seconds: float = 0.0
    failure: str | None = None
    two_item: bool = False


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
