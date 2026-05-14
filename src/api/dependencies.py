import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_jwt
from src.infrastructure.database import get_db, set_tenant_context
from src.repositories.embedding_repository import EmbeddingRepository
from src.services.matchmaking_service import MatchmakingService

security_scheme = HTTPBearer()

# --- AUTH ---


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    Dependency that verifies the JWT and returns the user payload.
    """
    token = credentials.credentials
    user_payload = decode_jwt(token)

    if "sub" not in user_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    return user_payload


async def get_current_tenant_id(
    user: dict = Depends(get_current_user),
) -> uuid.UUID:
    """
    Dependency that extracts tenant_id from the user payload.
    """
    tenant_id_str = user.get("tenantId")
    if not tenant_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenantId in token"
        )
    try:
        return uuid.UUID(tenant_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenantId format"
        )


# --- REPOSITORIES ---


async def get_embedding_repository(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
) -> EmbeddingRepository:
    """
    Dependency that provides an instance of the EmbeddingRepository with the database session.
    Sets the tenant context for RLS before returning.
    """
    await set_tenant_context(db, tenant_id)
    return EmbeddingRepository(db, tenant_id)


# --- SERVICES ---


async def get_matchmaking_service(
    repo: EmbeddingRepository = Depends(get_embedding_repository),
) -> MatchmakingService:
    """
    Dependency that provides an instance of the MatchmakingService with the required repository.
    """
    return MatchmakingService(repo)
