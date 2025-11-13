"""
Authentication endpoints for JWT-based authentication
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger

from .database import db
from .models import (
    LoginRequest,
    LoginResponse,
    TokenVerifyResponse,
    SuccessResponse
)
from .utils import verify_password, generate_token, get_italy_time_naive


router = APIRouter()


# ==================== Helper Functions ====================

async def get_current_user_from_token(authorization: Optional[str] = Header(None)) -> dict:
    """
    Get current user from Bearer token
    
    Args:
        authorization: Authorization header with Bearer token
    
    Returns:
        User dict with user_id, email, name, role, region
    
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mancante")
    
    token = authorization.split("Bearer ")[1]
    
    # Verify token in database
    query = """
    SELECT u.user_id, u.email, u.name, u.role, u.region, u.is_active
    FROM users u
    JOIN user_sessions us ON u.user_id = us.user_id
    WHERE us.token_hash = $1 AND us.expires_at > NOW() AND u.is_active = true
    """
    
    user = await db.fetchrow(query, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Token non valido o scaduto")
    
    return {
        "user_id": user['user_id'],
        "email": user['email'],
        "name": user['name'],
        "role": user['role'],
        "region": user['region']
    }


# ==================== Authentication Endpoints ====================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    User login endpoint
    
    Authenticates user credentials and creates session token
    """
    try:
        logger.info(f"🔐 Login attempt for: {request.email}")
        
        # Get user from database
        query = """
        SELECT user_id, email, name, role, region, password_hash, is_active
        FROM users
        WHERE email = $1
        """
        
        user = await db.fetchrow(query, request.email)
        
        if not user:
            logger.warning(f"❌ User {request.email} not found")
            raise HTTPException(
                status_code=401,
                detail="Email o password non corretti"
            )
        
        if not user['is_active']:
            logger.warning(f"❌ User {request.email} is not active")
            raise HTTPException(
                status_code=401,
                detail="Account disattivato. Contatta l'amministratore."
            )
        
        # Verify password
        if not verify_password(request.password, user['password_hash']):
            logger.warning(f"❌ Invalid password for user {request.email}")
            raise HTTPException(
                status_code=401,
                detail="Email o password non corretti"
            )
        
        logger.info(f"✅ User {user['email']} authenticated successfully")
        
        # Generate token
        token = generate_token(user['user_id'])
        
        # Calculate expiration time
        expire_hours = 24 if request.remember_me else 8
        expire_time = get_italy_time_naive() + timedelta(hours=expire_hours)
        
        # Save session in database
        session_query = """
        INSERT INTO user_sessions (user_id, token_hash, created_at, expires_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id) DO UPDATE
        SET token_hash = EXCLUDED.token_hash,
            expires_at = EXCLUDED.expires_at,
            last_activity = EXCLUDED.created_at
        """
        
        current_time = get_italy_time_naive()
        await db.execute(session_query, user['user_id'], token, current_time, expire_time)
        
        logger.info(f"✅ Session created for user {user['user_id']}")
        
        return LoginResponse(
            success=True,
            message="Login effettuato con successo",
            access_token=token,
            token_type="bearer",
            user={
                "user_id": user['user_id'],
                "email": user['email'],
                "name": user['name'],
                "role": user['role'],
                "region": user['region']
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Errore interno del server"
        )


@router.get("/verify", response_model=TokenVerifyResponse)
async def verify_token(current_user: dict = Depends(get_current_user_from_token)):
    """
    Verify token endpoint
    
    Checks if token is valid and returns user information
    """
    try:
        # Update last_activity
        update_query = """
        UPDATE user_sessions
        SET last_activity = $1
        WHERE user_id = $2
        """
        
        current_time = get_italy_time_naive()
        await db.execute(update_query, current_time, current_user['user_id'])
        
        return TokenVerifyResponse(
            valid=True,
            user=current_user
        )
        
    except Exception as e:
        logger.error(f"❌ Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Token non valido")


@router.post("/logout", response_model=SuccessResponse)
async def logout(authorization: Optional[str] = Header(None)):
    """
    User logout endpoint
    
    Invalidates current session token
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return SuccessResponse(
                success=True,
                message="Logout effettuato con successo"
            )
        
        token = authorization.split("Bearer ")[1]
        
        logger.info(f"🔐 Logout request for token: {token[:20]}...")
        
        # Delete session from database
        delete_query = """
        DELETE FROM user_sessions
        WHERE token_hash = $1
        """
        
        await db.execute(delete_query, token)
        
        logger.info("✅ Session deleted from database")
        
        return SuccessResponse(
            success=True,
            message="Logout effettuato con successo"
        )
        
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        # Always return success for logout
        return SuccessResponse(
            success=True,
            message="Logout effettuato con successo"
        )


@router.post("/cleanup-sessions")
async def cleanup_expired_sessions(current_user: dict = Depends(get_current_user_from_token)):
    """
    Cleanup expired sessions (admin only)
    
    Removes all expired sessions from database
    """
    try:
        # Check if user is admin
        if current_user['role'] != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Non autorizzato. Solo gli admin possono eseguire questa operazione."
            )
        
        # Delete expired sessions
        delete_query = """
        DELETE FROM user_sessions
        WHERE expires_at < NOW()
        """
        
        result = await db.execute(delete_query)
        
        logger.info(f"✅ Expired sessions cleaned up")
        
        return SuccessResponse(
            success=True,
            message="Sessioni scadute rimosse con successo"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Cleanup sessions error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Errore durante la pulizia delle sessioni"
        )
