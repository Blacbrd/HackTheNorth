from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_robot_job_service
from app.schemas.robot import FAILURES, HistoryResponse, RobotJobResponse
from app.services.robot_jobs import RobotJobService

router = APIRouter(prefix="/robot", tags=["robot"])


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
    """Force a failure. Exists so the failure states can be exercised without
    staging a real obstacle in front of the robot."""
    if failure not in FAILURES:
        raise HTTPException(status_code=400, detail=f"Unknown failure. Use one of: {', '.join(FAILURES)}")
    return service.fail(failure)


@router.get("/history", response_model=HistoryResponse)
def history(service: RobotJobService = Depends(get_robot_job_service)) -> HistoryResponse:
    return HistoryResponse(entries=service.history())
