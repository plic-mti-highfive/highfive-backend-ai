import uuid
from typing import List

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_matchmaking_service
from src.core.logger import get_logger
from src.services.matchmaking_service import MatchmakingService

logger = get_logger(__name__)

router = APIRouter(prefix="/matchmaking", tags=["Matchmaking"])


@router.get("/users/{user_id}/projects", response_model=List[uuid.UUID])
async def get_projects_for_user(
    user_id: uuid.UUID,
    tags: List[str] | None = Query(default=None),
    limit: int = 10,
    matchmaking_service: MatchmakingService = Depends(get_matchmaking_service),
):
    """
    Endpoint to get project recommendations for a user.
    Optional query parameter 'tags' can be used to filter projects by specific tags. (not implemented yet)
    Use mean polling to fetch the most relevant projects for the user based on their identity and interests.
    """
    logger.info(
        f"Fetching project recommendations for user {user_id} (tags: {tags}, limit: {limit})"
    )

    result = await matchmaking_service.get_project_recommendations_for_user(
        user_id=user_id, tags=tags, limit=limit
    )
    return result


@router.get("/projects/{project_id}/users", response_model=List[uuid.UUID])
async def get_users_for_project(
    project_id: uuid.UUID,
    limit: int = 10,
    matchmaking_service: MatchmakingService = Depends(get_matchmaking_service),
):
    """Endpoint to get user recommendations for a project."""
    logger.info(f"Fetching user recommendations for project {project_id} (limit: {limit})")
    result = await matchmaking_service.get_user_recommendations_for_project(
        project_id=project_id, limit=limit
    )
    logger.info(f"Found {len(result)} user recommendations for project {project_id}")
    return result


@router.get("/trending", response_model=List[uuid.UUID])
async def get_trending_projects(
    limit: int = 10,
    matchmaking_service: MatchmakingService = Depends(get_matchmaking_service),
):
    """
    Endpoint to get trending projects based on recent interactions and time-decay.
    This will return projects that are currently popular, giving more weight to recent interactions.
    """
    logger.info(f"Fetching trending projects (limit: {limit})")

    # Appelle la méthode qu'on a créée dans le Repository (Time-Decay)
    # Tu devras juste ajouter un petit passe-plat dans ton MatchmakingService pour l'appeler
    result = await matchmaking_service.repo.get_trending_projects(limit=limit)
    return [proj.entity_id for proj in result]
