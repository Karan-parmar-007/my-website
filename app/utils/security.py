# utils/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import secrets

from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status
# changed: use python-jose
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.config import security_settings

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    # Generate a random salt
    salt = secrets.token_hex(32)  # 32 bytes = 64 hex characters
    
    # Combine password and salt
    password_salt = password + salt
    
    # Hash with SHA-256
    hash_obj = hashlib.sha256(password_salt.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    
    # Return salt + hash (salt first 64 chars, hash remaining)
    return salt + password_hash

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    try:
        # Extract salt (first 64 characters) and hash (remaining)
        salt = hashed_password[:64]
        stored_hash = hashed_password[64:]
        
        # Hash the plain password with the extracted salt
        password_salt = plain_password + salt
        hash_obj = hashlib.sha256(password_salt.encode('utf-8'))
        password_hash = hash_obj.hexdigest()
        
        # Compare hashes
        return password_hash == stored_hash
    except (IndexError, ValueError):
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=security_settings.JWT_EXPIRATION_Days,
            minutes=security_settings.JWT_EXPIRATION_MINUTES
        )
    
    to_encode.update({"exp": expire})
    # use jose.jwt.encode
    encoded_jwt = jwt.encode(
        to_encode, 
        security_settings.JWT_SECRET, 
        algorithm=security_settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify a JWT token and return its payload."""
    try:
        payload = jwt.decode(
            token, 
            security_settings.JWT_SECRET, 
            algorithms=[security_settings.JWT_ALGORITHM]
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )



