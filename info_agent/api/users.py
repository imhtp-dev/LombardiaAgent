"""
User management endpoints (CRUD operations)
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from loguru import logger

from .database import db
from .models import (
    UserCreate,
    UserResponse,
    UserToggleStatusResponse,
    SuccessResponse
)
from .utils import (
    generate_password,
    hash_password,
    send_registration_email,
    get_italy_time_naive
)
from .auth import get_current_user_from_token


router = APIRouter()


# ==================== User Management Endpoints ====================

@router.post("", response_model=dict)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Create a new user and send credentials via email
    
    Requires authentication
    """
    try:
        logger.info(f"👤 Creating new user: {user_data.email}")
        
        # Validate input
        if not user_data.nome.strip():
            raise HTTPException(status_code=400, detail="Il nome è obbligatorio")
        
        if not user_data.cognome.strip():
            raise HTTPException(status_code=400, detail="Il cognome è obbligatorio")
        
        if not user_data.email.strip():
            raise HTTPException(status_code=400, detail="L'email è obbligatoria")
        
        if not user_data.ruolo.strip():
            raise HTTPException(status_code=400, detail="Il ruolo è obbligatorio")
        
        # Check if email already exists
        check_query = "SELECT user_id FROM users WHERE email = $1"
        existing_user = await db.fetchrow(check_query, user_data.email.strip())
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Un utente con questa email esiste già"
            )
        
        # Generate password and hash it
        password = generate_password()
        password_hash = hash_password(password)
        
        # Determine region and role for database
        region = "master" if user_data.ruolo == "master" else user_data.ruolo
        db_role = "admin" if user_data.ruolo == "master" else "operator"
        
        # Create full name
        nome_completo = f"{user_data.nome.strip()} {user_data.cognome.strip()}"
        
        # Insert user into database
        insert_query = """
        INSERT INTO users (email, name, password_hash, role, region, is_active, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, true, $6, $7)
        RETURNING user_id
        """
        
        current_time = get_italy_time_naive()
        user_id = await db.fetchval(
            insert_query,
            user_data.email.strip(),
            nome_completo,
            password_hash,
            db_role,
            region,
            current_time,
            current_time
        )
        
        if not user_id:
            raise HTTPException(
                status_code=500,
                detail="Errore durante la creazione dell'utente"
            )
        
        logger.info(f"✅ User created in database with ID: {user_id}")
        
        # Send email with credentials
        email_sent = await send_registration_email(
            user_data.email.strip(),
            user_data.nome.strip(),
            user_data.cognome.strip(),
            password,
            user_data.ruolo
        )
        
        if not email_sent:
            logger.warning(f"⚠️ Email not sent to {user_data.email}, but user created")
        
        return {
            "success": True,
            "message": "Utente creato con successo! Credenziali inviate via email.",
            "user_id": user_id,
            "email_sent": email_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nella creazione dell'utente: {str(e)}"
        )


@router.get("", response_model=List[UserResponse])
async def list_users(current_user: dict = Depends(get_current_user_from_token)):
    """
    Get list of all users
    
    Requires authentication
    """
    try:
        logger.info("📋 Getting all users")
        
        query = """
        SELECT user_id, email, name, role, region, is_active, created_at, updated_at
        FROM users
        ORDER BY created_at DESC
        """
        
        users = await db.fetch(query)
        
        user_list = []
        for user in users:
            # Split name into first and last name
            name_parts = user['name'].split(' ', 1)
            nome = name_parts[0] if name_parts else ""
            cognome = name_parts[1] if len(name_parts) > 1 else ""
            
            user_list.append(UserResponse(
                user_id=user['user_id'],
                email=user['email'],
                nome=nome,
                cognome=cognome,
                ruolo=user['region'],  # Display region as ruolo
                region=user['region'],
                is_active=user['is_active'],
                created_at=user['created_at'],
                updated_at=user['updated_at']
            ))
        
        logger.info(f"✅ Found {len(user_list)} users")
        return user_list
        
    except Exception as e:
        logger.error(f"❌ Error getting users: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero utenti: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get a specific user by ID
    
    Requires authentication
    """
    try:
        logger.info(f"🔍 Getting user: {user_id}")
        
        query = """
        SELECT user_id, email, name, role, region, is_active, created_at, updated_at
        FROM users
        WHERE user_id = $1
        """
        
        user = await db.fetchrow(query, user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        
        # Split name into first and last name
        name_parts = user['name'].split(' ', 1)
        nome = name_parts[0] if name_parts else ""
        cognome = name_parts[1] if len(name_parts) > 1 else ""
        
        return UserResponse(
            user_id=user['user_id'],
            email=user['email'],
            nome=nome,
            cognome=cognome,
            ruolo=user['region'],
            region=user['region'],
            is_active=user['is_active'],
            created_at=user['created_at'],
            updated_at=user['updated_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero utente: {str(e)}"
        )


@router.put("/{user_id}/toggle-status", response_model=UserToggleStatusResponse)
async def toggle_user_status(
    user_id: int,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Toggle user active/inactive status
    
    Requires authentication
    """
    try:
        logger.info(f"🔄 Toggling status for user ID: {user_id}")
        
        # Get current status
        user_query = "SELECT user_id, is_active FROM users WHERE user_id = $1"
        user = await db.fetchrow(user_query, user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        
        # Toggle status
        new_status = not user['is_active']
        
        # Update user status
        update_query = """
        UPDATE users
        SET is_active = $1, updated_at = $2
        WHERE user_id = $3
        """
        
        current_time = get_italy_time_naive()
        await db.execute(update_query, new_status, current_time, user_id)
        
        # If disabled, delete active sessions
        if not new_status:
            delete_sessions_query = "DELETE FROM user_sessions WHERE user_id = $1"
            await db.execute(delete_sessions_query, user_id)
            logger.info(f"🔒 Sessions deleted for disabled user {user_id}")
        
        action = "attivato" if new_status else "disattivato"
        
        return UserToggleStatusResponse(
            success=True,
            message=f"Utente {action} con successo",
            new_status=new_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error toggling user status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel cambio stato utente: {str(e)}"
        )


@router.post("/{user_id}/resend-credentials", response_model=dict)
async def resend_credentials(
    user_id: int,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Resend credentials to user (generates new password)
    
    Requires authentication
    """
    try:
        logger.info(f"📧 Resending credentials for user ID: {user_id}")
        
        # Get user data
        user_query = """
        SELECT user_id, email, name, role, region, is_active
        FROM users
        WHERE user_id = $1
        """
        
        user = await db.fetchrow(user_query, user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        
        if not user['is_active']:
            raise HTTPException(status_code=400, detail="L'utente è disattivato")
        
        # Generate new password
        new_password = generate_password()
        password_hash = hash_password(new_password)
        
        # Update password in database
        update_query = """
        UPDATE users
        SET password_hash = $1, updated_at = $2
        WHERE user_id = $3
        """
        
        current_time = get_italy_time_naive()
        await db.execute(update_query, password_hash, current_time, user_id)
        
        # Split name into first and last name
        name_parts = user['name'].split(' ', 1)
        nome = name_parts[0] if name_parts else ""
        cognome = name_parts[1] if len(name_parts) > 1 else ""
        
        # Send email with new credentials
        email_sent = await send_registration_email(
            user['email'],
            nome,
            cognome,
            new_password,
            user['region']
        )
        
        return {
            "success": True,
            "message": "Nuove credenziali generate e inviate via email",
            "email_sent": email_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error resending credentials: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel rinvio credenziali: {str(e)}"
        )


@router.delete("/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Delete a user
    
    Requires authentication
    """
    try:
        logger.info(f"🗑️ Deleting user ID: {user_id}")
        
        # Check if user exists
        user_query = "SELECT user_id FROM users WHERE user_id = $1"
        user = await db.fetchrow(user_query, user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="Utente non trovato")
        
        # Delete user sessions first
        delete_sessions_query = "DELETE FROM user_sessions WHERE user_id = $1"
        await db.execute(delete_sessions_query, user_id)
        
        # Delete user
        delete_query = "DELETE FROM users WHERE user_id = $1"
        await db.execute(delete_query, user_id)
        
        logger.info(f"✅ User {user_id} deleted successfully")
        
        return SuccessResponse(
            success=True,
            message="Utente eliminato con successo"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting user: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nell'eliminazione utente: {str(e)}"
        )
