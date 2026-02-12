# utils/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import hashlib
import secrets

from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from passlib.context import CryptContext

from app.config import security_settings

SECRET_KEY = security_settings.JWT_SECRET
ALGORITHM = security_settings.JWT_ALGORITHM

# Token expiry from config
ACCESS_TOKEN_EXPIRE = timedelta(minutes=security_settings.ACCESS_TOKEN_EXPIRY_MINUTES)
ACCESS_TOKEN_EXPIRE_SECONDS = int(ACCESS_TOKEN_EXPIRE.total_seconds())
REFRESH_TOKEN_EXPIRE = timedelta(days=security_settings.REFRESH_TOKEN_EXPIRY_DAYS)
REFRESH_TOKEN_EXPIRE_SECONDS = int(REFRESH_TOKEN_EXPIRE.total_seconds())

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    payload: Dict[str, Any] = {"sub": subject, "type": "access"}
    if additional_claims:
        payload.update(additional_claims)
    expires = _utcnow() + (expires_delta or ACCESS_TOKEN_EXPIRE)
    payload["exp"] = expires
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def issue_access_token(
    subject: str,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    token = create_access_token(subject, ACCESS_TOKEN_EXPIRE, additional_claims)
    return {
        "access_token": token,
        "token_type": "bearer",
        "access_token_expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
    }

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        return None
    except JWTError:
        return None

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    return decode_token(token)

def verify_token(token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if expected_type and payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload


# ----------------------------------------
# 🔹 OTP and Password Reset Utilities
# ----------------------------------------

def generate_otp() -> str:
    """
    Generate a 6-digit numeric OTP.
    
    Returns:
        6-digit OTP as string
    """
    import random
    return str(random.randint(100000, 999999))


def hash_otp(otp: str) -> str:
    """
    Hash OTP using bcrypt for secure storage.
    
    Args:
        otp: Plain text OTP
    
    Returns:
        Hashed OTP
    """
    return pwd_context.hash(otp)


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """
    Verify OTP against its hash.
    
    Args:
        plain_otp: Plain text OTP from user
        hashed_otp: Hashed OTP from database
    
    Returns:
        True if OTP matches, False otherwise
    """
    return pwd_context.verify(plain_otp, hashed_otp)


def create_password_reset_token(email: str) -> str:
    """
    Create a short-lived JWT token for password reset (5 minutes).
    
    Args:
        email: User's email address
    
    Returns:
        JWT token string
    """
    payload: Dict[str, Any] = {
        "sub": email,
        "email": email,
        "type": "password_reset"
    }
    expires = _utcnow() + timedelta(minutes=5)
    payload["exp"] = expires
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ----------------------------------------
# 🔹 Refresh Token Utilities
# ----------------------------------------

def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for secure storage.
    Unlike bcrypt, SHA-256 is deterministic so we can look up tokens.
    
    Args:
        token: Plain text token
    
    Returns:
        SHA-256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token() -> Tuple[str, str, datetime]:
    """
    Generate a secure refresh token.
    
    Returns:
        Tuple of (plain_token, token_hash, expires_at)
        - plain_token: Send this to the client (in httpOnly cookie)
        - token_hash: Store this in the database
        - expires_at: When the token expires
    """
    # Generate 64 bytes of random data, encode as hex (128 chars)
    plain_token = secrets.token_hex(64)
    token_hash = hash_token(plain_token)
    expires_at = _utcnow() + REFRESH_TOKEN_EXPIRE
    return plain_token, token_hash, expires_at


def verify_refresh_token_hash(plain_token: str, stored_hash: str) -> bool:
    """
    Verify a refresh token against its stored hash.
    
    Args:
        plain_token: Plain text token from client
        stored_hash: SHA-256 hash from database
    
    Returns:
        True if token matches, False otherwise
    """
    return hash_token(plain_token) == stored_hash


def get_refresh_token_expiry() -> datetime:
    """
    Get the expiry datetime for a new refresh token.
    
    Returns:
        datetime when the token should expire
    """
    return _utcnow() + REFRESH_TOKEN_EXPIRE
