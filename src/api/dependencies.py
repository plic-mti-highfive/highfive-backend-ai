from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_jwt
from src.infrastructure.database import get_db
from src.repositories.embedding_repository import EmbeddingRepository

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


# --- REPOSITORIES ---


def get_embedding_repository(db: AsyncSession = Depends(get_db)) -> EmbeddingRepository:
    """
    Dependency that provides an instance of the EmbeddingRepository with the database session.
    """
    return EmbeddingRepository(db)
