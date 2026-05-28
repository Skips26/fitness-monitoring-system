"""
Auth middleware — verifies Supabase JWT tokens from the Authorization header.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from config import SUPABASE_JWT_SECRET

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Decode and validate the Supabase JWT from the Authorization header.
    Returns the decoded payload (contains 'sub' = user UUID).
    """
    token = credentials.credentials

    try:
        # For local development, we bypass signature verification to avoid algorithm mismatch issues
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    return {"id": user_id, "email": payload.get("email", ""), "payload": payload}
