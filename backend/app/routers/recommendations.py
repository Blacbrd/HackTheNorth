from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_recommendation_service
from app.schemas.recommendations import RecommendationRequest, RecommendationResponse
from app.services.recommendations import (
    InvalidRecommendationError,
    RecommendationProviderError,
    RecommendationService,
    RecommendationUnavailableError,
    RobotDispatchError,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _run(request: RecommendationRequest, source: str, send_to_robot: bool, service: RecommendationService) -> RecommendationResponse:
    try:
        return service.recommend(request.user_input, source=source, send_to_robot=send_to_robot)
    except RecommendationUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except RecommendationProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None
    except InvalidRecommendationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None
    except RobotDispatchError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None


@router.post("/app", response_model=RecommendationResponse)
def recommend_from_app(request: RecommendationRequest, service: RecommendationService = Depends(get_recommendation_service)) -> RecommendationResponse:
    return _run(request, source="app", send_to_robot=True, service=service)


@router.post("/robot", response_model=RecommendationResponse)
def recommend_from_robot(request: RecommendationRequest, service: RecommendationService = Depends(get_recommendation_service)) -> RecommendationResponse:
    return _run(request, source="robot", send_to_robot=False, service=service)
