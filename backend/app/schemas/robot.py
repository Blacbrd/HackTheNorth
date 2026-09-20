from datetime import datetime

from pydantic import BaseModel

# Two stage lists because a two-item run genuinely has an extra step (drop the
# first item, then the second) rather than just taking longer at one of these.
SINGLE_STAGES = ("picking", "driving", "arrived")
TWO_ITEM_STAGES = ("queued", "dropping_first", "dropping_second", "arrived")
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
    # True only when no real robot is attached, i.e. send_pick_command just
    # printed. A real run reports real stdout-driven stages.
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
