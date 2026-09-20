from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_robot_job_service
from app.schemas.robot import FAILURES, SINGLE_STAGES, HistoryResponse, RobotJobResponse
from app.services.robot_jobs import RobotJobService

router = APIRouter(prefix="/robot", tags=["robot"])

_KNOWN_STAGES = set(SINGLE_STAGES)


@router.get("/job", response_model=RobotJobResponse)
def current_job(service: RobotJobService = Depends(get_robot_job_service)) -> RobotJobResponse:
    return service.current()


@router.post("/job/recall", response_model=RobotJobResponse)
def recall(service: RobotJobService = Depends(get_robot_job_service)) -> RobotJobResponse:
    return service.recall()


@router.post("/job/clear", response_model=RobotJobResponse)
def clear(service: RobotJobService = Depends(get_robot_job_service)) -> RobotJobResponse:
    """Acknowledge a finished or failed job so the app stops showing it."""
    return service.clear()


@router.post("/job/fail/{failure}", response_model=RobotJobResponse)
def fail(failure: str, service: RobotJobService = Depends(get_robot_job_service)) -> RobotJobResponse:
    """Record a failure reported by the robot integration."""
    if failure not in FAILURES:
        raise HTTPException(status_code=400, detail=f"Unknown failure. Use one of: {', '.join(FAILURES)}")
    return service.fail(failure)


@router.post("/job/stage/{stage}", response_model=RobotJobResponse)
def advance_stage(stage: str, service: RobotJobService = Depends(get_robot_job_service)) -> RobotJobResponse:
    """Optional push path: the robot script can POST its stage here instead of
    (or in addition to) printing it to stdout for RobotClient to parse."""
    if stage not in _KNOWN_STAGES:
        raise HTTPException(status_code=400, detail=f"Unknown stage. Use one of: {', '.join(sorted(_KNOWN_STAGES))}")
    service.advance(stage)
    return service.current()


@router.get("/history", response_model=HistoryResponse)
def history(service: RobotJobService = Depends(get_robot_job_service)) -> HistoryResponse:
    return HistoryResponse(entries=service.history())
