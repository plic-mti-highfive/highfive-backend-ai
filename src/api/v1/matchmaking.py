import uuid
from typing import List

from fastapi import APIRouter, Depends

from src.api.dependencies import get_matchmaking_service
from src.services.matchmaking_service import MatchmakingService

router = APIRouter(prefix="/matchmaking", tags=["Matchmaking"])


@router.get("/users/{user_id}/projects", response_model=List[uuid.UUID])
async def get_projects_for_user(
    user_id: uuid.UUID,
    limit: int = 10,
    matchmaking_service: MatchmakingService = Depends(get_matchmaking_service),
):
    """Endpoint to get project recommendations for a user."""
    return await matchmaking_service.get_project_recommendations_for_user(
        user_id=user_id, limit=limit
    )


@router.get("/projects/{project_id}/users", response_model=List[uuid.UUID])
async def get_users_for_project(
    project_id: uuid.UUID,
    limit: int = 10,
    matchmaking_service: MatchmakingService = Depends(get_matchmaking_service),
):
    """Endpoint to get user recommendations for a project."""
    return await matchmaking_service.get_user_recommendations_for_project(
        project_id=project_id, limit=limit
    )
