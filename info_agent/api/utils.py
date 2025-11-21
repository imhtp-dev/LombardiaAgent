"""
Utility functions for authentication, email, and timezone handling
"""

import os
import bcrypt
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from loguru import logger


# ==================== Password Utilities ====================

def generate_password(length: int = 7) -> str:
    """
    Generate a secure random password with special characters
    
    Args:
        length: Password length (default: 7)
    
    Returns:
        Random password string with at least 1 special character
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    
    # Ensure at least one special character
    password = secrets.choice("!@#$%^&*")  # Start with a special char
    password += ''.join(secrets.choice(alphabet) for _ in range(length - 1))
    
    # Shuffle to randomize position of special character
    password_list = list(password)
    secrets.SystemRandom().shuffle(password_list)
    
    return ''.join(password_list)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"❌ Error verifying password: {e}")
        return False


# ==================== Email Utilities ====================

async def send_registration_email(
    email: str,
    nome: str,
    cognome: str,
    password: str,
    ruolo: str
) -> bool:
    """
    Send registration email with credentials using SendGrid
    
    Args:
        email: User email address
        nome: First name
        cognome: Last name
        password: Generated password
        ruolo: User role
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        sendgrid_from_email = os.getenv("SENDGRID_FROM_EMAIL", "registration@voilaagentdash.com")
        
        if not sendgrid_api_key:
            logger.error("❌ SENDGRID_API_KEY not configured")
            return False
        
        nome_completo = f"{nome} {cognome}"
        
        # HTML email template
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .header {{
                    background-color: #667eea;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .credentials {{
                    background-color: #f0f0f0;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Benvenuto in Voilà Voice Agent Dashboard</h1>
                </div>
                <div class="content">
                    <p>Ciao <strong>{nome_completo}</strong>,</p>
                    <p>Il tuo account è stato creato con successo!</p>
                    <p>Ecco le tue credenziali di accesso:</p>
                    
                    <div class="credentials">
                        <p><strong>Email:</strong> {email}</p>
                        <p><strong>Password:</strong> {password}</p>
                        <p><strong>Ruolo:</strong> {ruolo}</p>
                    </div>
                    
                    <p>Puoi accedere alla dashboard al seguente link:</p>
                    <p><a href="https://voilavoicedashboardcerba-dzdch8bhcddzdjak.francecentral-01.azurewebsites.net/login" style="color: #667eea;">https://voilavoicedashboardcerba-dzdch8bhcddzdjak.francecentral-01.azurewebsites.net/login</a></p>
                    
                    <p style="margin-top: 30px;">Per la tua sicurezza, ti consigliamo di cambiare la password al primo accesso.</p>
                    
                    <p>Se hai domande, non esitare a contattarci.</p>
                    
                    <p>Cordiali saluti,<br>Il team Voilà</p>
                </div>
                <div class="footer">
                    <p>Questa è una email automatica, si prega di non rispondere.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
        Benvenuto in Voilà Voice Agent Dashboard!
        
        Ciao {nome_completo},
        
        Il tuo account è stato creato con successo!
        
        Credenziali di accesso:
        - Email: {email}
        - Password: {password}
        - Ruolo: {ruolo}
        
        Link dashboard: https://voilavoicedashboardcerba-dzdch8bhcddzdjak.francecentral-01.azurewebsites.net/login
        
        Per la tua sicurezza, ti consigliamo di cambiare la password al primo accesso.
        
        Cordiali saluti,
        Il team Voilà
        """
        
        # Create and send email
        message = Mail(
            from_email=sendgrid_from_email,
            to_emails=email,
            subject='Voilà Voice Agent Dashboard - Credenziali di Accesso',
            plain_text_content=text_content,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        logger.info(f"✅ Registration email sent to {email}, status: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error sending registration email to {email}: {e}")
        return False


# ==================== Timezone Utilities ====================

def get_italy_time() -> datetime:
    """
    Get current time in Italy timezone (UTC+2 / UTC+1 depending on DST)
    
    Returns:
        Current datetime in Italy timezone
    """
    # Italy is UTC+1 (winter) or UTC+2 (summer)
    # For simplicity, using UTC+2 as stated in original code
    italy_tz = timezone(timedelta(hours=2))
    return datetime.now(italy_tz)


def get_italy_time_naive() -> datetime:
    """
    Get current time in Italy timezone as naive datetime (for PostgreSQL)
    
    Returns:
        Current datetime in Italy timezone without timezone info
    """
    italy_time = get_italy_time()
    return italy_time.replace(tzinfo=None)


# ==================== Token Generation ====================

def generate_token(user_id: int) -> str:
    """
    Generate a JWT-like token for session management
    
    Args:
        user_id: User ID from database
    
    Returns:
        Generated token string
    """
    import time
    return f"user-token-{user_id}-{int(time.time())}-{secrets.token_hex(16)}"


# ==================== ID Generation ====================

def generate_pinecone_id(region: str, qa_id: int) -> str:
    """
    Generate unique ID for Pinecone vector
    
    Args:
        region: Region name
        qa_id: Q&A ID from database
    
    Returns:
        Unique Pinecone ID
    """
    import time
    return f"qa_{region}_{qa_id}_{int(time.time())}"
