# utils/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from passlib.context import CryptContext

from app.config import security_settings

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = security_settings.JWT_SECRET
ALGORITHM = security_settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE = timedelta(days=max(security_settings.JWT_EXPIRATION_Days, 1))
ACCESS_TOKEN_EXPIRE_SECONDS = int(ACCESS_TOKEN_EXPIRE.total_seconds())

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



