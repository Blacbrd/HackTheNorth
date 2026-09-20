"""Tracks the one job the robot is doing, plus a short request history.

Stages are driven by the robot process's stdout: `RobotClient` reads the
workflow script's output line by line and calls `advance()` with whatever
stage that line implies. Nothing in here invents progress on a timer any
more -- if the robot process stalls, so does the stage reported here.

Keeping that state here rather than in the app still buys something real.
Every client agrees on one job, the history survives a phone reload, and the
robot side can report progress either by printing to stdout (parsed by
`RobotClient`) or by POSTing to `/robot/job/stage/{stage}` directly.

State is in memory, so a server restart clears it. That is fine for a single
demo machine and wrong for anything else.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from threading import RLock

from app.schemas.recommendations import GeminiRecommendation
from app.schemas.robot import (
    SINGLE_STAGES,
    TWO_ITEM_STAGES,
    HistoryEntry,
    RobotJobItem,
    RobotJobResponse,
)

HISTORY_LIMIT = 20


class RobotJobService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at: float | None = None
        self._stages: tuple[str, ...] = ()
        self._stage_index = -1
        self._items: list[RobotJobItem] = []
        self._two_item = False
        self._failure: str | None = None
        self._simulated = True
        self._history: list[HistoryEntry] = []

    # -- job ---------------------------------------------------------------
    def start(
        self,
        recommendations: list[GeminiRecommendation],
        user_input: str,
        two_item: bool = False,
        simulated: bool = True,
    ) -> None:
        with self._lock:
            self._started_at = time.monotonic()
            self._stages = TWO_ITEM_STAGES if two_item else SINGLE_STAGES
            self._stage_index = 0
            self._items = [
                RobotJobItem(shelf_number=rec.shelf_number, item=rec.item) for rec in recommendations
            ]
            self._two_item = two_item
            self._failure = None
            self._simulated = simulated
            first = recommendations[0]
            self._record(
                user_input=user_input,
                item=first.item,
                shelf_number=first.shelf_number,
                succeeded=True,
                failure=None,
            )

    def advance(self, stage: str) -> None:
        """Move to `stage` if it is a later stage of the current job.

        Unknown stage keys are ignored rather than raising, since they may be
        prose from a robot script version this backend does not recognize
        yet -- better to sit still than to jump somewhere wrong. Stages never
        move backwards: stdout can repeat a line (retries, logging) and that
        must not undo progress already reported.
        """
        with self._lock:
            if self._started_at is None or not self._stages:
                return
            try:
                index = self._stages.index(stage)
            except ValueError:
                return
            if index > self._stage_index:
                self._stage_index = index

    def complete(self) -> None:
        with self._lock:
            if self._started_at is None or not self._stages:
                return
            self._stage_index = len(self._stages) - 1

    def current(self) -> RobotJobResponse:
        with self._lock:
            if self._started_at is None:
                return RobotJobResponse(active=False)
            elapsed = time.monotonic() - self._started_at
            index = self._stage_index
            stages = list(self._stages)
            first = self._items[0] if self._items else None
            return RobotJobResponse(
                active=self._failure is None and index < len(stages) - 1,
                stage=stages[index] if 0 <= index < len(stages) else None,
                stage_index=index,
                stages=stages,
                shelf_number=first.shelf_number if first else None,
                item=first.item if first else None,
                items=list(self._items),
                elapsed_seconds=round(elapsed, 1),
                failure=self._failure,
                two_item=self._two_item,
                simulated=self._simulated,
            )

    def recall(self) -> RobotJobResponse:
        """Stop the run. The real robot has no stop command, so this only
        clears the server's idea of the job."""
        with self._lock:
            self._reset()
            return RobotJobResponse(active=False)

    def clear(self) -> RobotJobResponse:
        with self._lock:
            self._reset()
            return RobotJobResponse(active=False)

    def fail(self, failure: str) -> RobotJobResponse:
        """Record a failure at whatever stage the job is currently at.

        Earlier versions tried to guess which stage each failure kind
        "belongs" to; now that stage advancement is real, the current index
        already is that stage, so recording the failure is enough.
        """
        with self._lock:
            if self._started_at is None:
                return RobotJobResponse(active=False)
            self._failure = failure
            if self._history:
                previous = self._history[0]
                self._history[0] = previous.model_copy(
                    update={"succeeded": False, "failure": failure, "item": None}
                )
            return self.current()

    def _reset(self) -> None:
        self._started_at = None
        self._stages = ()
        self._stage_index = -1
        self._items = []
        self._two_item = False
        self._failure = None
        self._simulated = True

    # -- history -----------------------------------------------------------
    def history(self) -> list[HistoryEntry]:
        with self._lock:
            return list(self._history)

    def record_failure(self, user_input: str, failure: str) -> None:
        with self._lock:
            self._record(
                user_input=user_input,
                item=None,
                shelf_number=None,
                succeeded=False,
                failure=failure,
            )

    def _record(
        self,
        user_input: str,
        item: str | None,
        shelf_number: int | None,
        succeeded: bool,
        failure: str | None,
    ) -> None:
        self._history.insert(
            0,
            HistoryEntry(
                id=uuid.uuid4().hex,
                user_input=user_input,
                item=item,
                shelf_number=shelf_number,
                succeeded=succeeded,
                failure=failure,
                created_at=datetime.now(timezone.utc),
            ),
        )
        del self._history[HISTORY_LIMIT:]
