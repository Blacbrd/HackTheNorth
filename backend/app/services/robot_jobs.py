"""Tracks the one job the robot is doing, plus a short request history.

The real robot reports nothing back yet: `RobotClient.send_pick_command` just
prints. So the stage a caller sees here advances on a timer rather than on
anything the hardware said, and every response carries `simulated: true` to say
so out loud.

Keeping that timer here rather than in the app still buys something real. Every
client agrees on one job, the history survives a phone reload, and swapping in
a robot that reports its own progress means replacing `_stage_for` alone.

State is in memory, so a server restart clears it. That is fine for a single
demo machine and wrong for anything else.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from threading import RLock

from app.schemas.recommendations import GeminiRecommendation
from app.schemas.robot import STAGES, HistoryEntry, RobotJobResponse

# How long each stage is assumed to take, in seconds. Only the last entry's
# absence matters: "arrived" is terminal and the job stops advancing there.
STAGE_SECONDS = (2.0, 6.0, 5.0, 6.0)
HISTORY_LIMIT = 20

# Where each failure interrupts the run: a missing item is discovered at the
# pick, a blocked route on the drive out, a fault on the way back.
FAILURE_STAGE = {"missing": 2, "blocked": 1, "fault": 3}


class RobotJobService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at: float | None = None
        self._shelf_number: int | None = None
        self._item: str | None = None
        self._failure: str | None = None
        self._simulated = True
        self._history: list[HistoryEntry] = []

    # -- job ---------------------------------------------------------------
    def start(
        self,
        recommendation: GeminiRecommendation,
        user_input: str,
        simulated: bool = True,
    ) -> None:
        with self._lock:
            self._started_at = time.monotonic()
            self._shelf_number = recommendation.shelf_number
            self._item = recommendation.item
            self._failure = None
            self._simulated = simulated
            self._record(
                user_input=user_input,
                item=recommendation.item,
                shelf_number=recommendation.shelf_number,
                succeeded=True,
                failure=None,
            )

    def current(self) -> RobotJobResponse:
        with self._lock:
            if self._started_at is None:
                return RobotJobResponse(active=False)
            elapsed = time.monotonic() - self._started_at
            index = (
                FAILURE_STAGE.get(self._failure, 0)
                if self._failure
                else self._stage_for(elapsed)
            )
            return RobotJobResponse(
                active=self._failure is None and index < len(STAGES) - 1,
                stage=STAGES[index],
                stage_index=index,
                shelf_number=self._shelf_number,
                item=self._item,
                elapsed_seconds=round(elapsed, 1),
                failure=self._failure,
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

    @staticmethod
    def _stage_for(elapsed: float) -> int:
        total = 0.0
        for index, seconds in enumerate(STAGE_SECONDS):
            total += seconds
            if elapsed < total:
                return index
        return len(STAGES) - 1

    def _reset(self) -> None:
        self._started_at = None
        self._shelf_number = None
        self._item = None
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
