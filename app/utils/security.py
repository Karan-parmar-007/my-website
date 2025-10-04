# utils/security.py
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt 


from passlib.context import CryptContext

# Create a password context for bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

