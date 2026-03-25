"""
Authentication helpers: password hashing, JWT creation/validation, and
FastAPI dependency functions for extracting the current user from a request.

Two types of tokens are issued:
- **Access token** — short-lived (configured by ``ACCESS_TOKEN_EXPIRE_MINUTES``).
- **Refresh token** — longer-lived (``REFRESH_TOKEN_EXPIRE_DAYS``); carries
  an extra ``"type": "refresh"`` claim so it can be distinguished from access
  tokens and cannot be used directly to authenticate API calls.
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

settings = get_settings()

# bcrypt is the hashing algorithm; "deprecated='auto'" will automatically
# re-hash passwords stored in older schemes when the user next logs in.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# The tokenUrl tells Swagger UI where to redirect for the login form.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare a plain-text password against its bcrypt hash.

    Args:
        plain_password: The raw password provided by the user.
        hashed_password: The bcrypt hash stored in the database.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plain-text password with bcrypt.

    Args:
        password: The raw password to hash.

    Returns:
        A bcrypt hash string suitable for database storage.
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> None:
    """
    Enforce the configured password policy on a candidate password.

    Checks are controlled by ``Settings.PASSWORD_MIN_LENGTH``,
    ``Settings.PASSWORD_REQUIRE_LETTER``, and
    ``Settings.PASSWORD_REQUIRE_DIGIT``.

    Args:
        password: The candidate password to validate.

    Raises:
        ValueError: If the password does not meet the configured policy.
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
    if settings.PASSWORD_REQUIRE_LETTER and not any(ch.isalpha() for ch in password):
        raise ValueError("Password must contain at least one letter")
    if settings.PASSWORD_REQUIRE_DIGIT and not any(ch.isdigit() for ch in password):
        raise ValueError("Password must contain at least one digit")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Claims to include in the token payload (typically ``{"sub": username}``).
        expires_delta: How long until the token expires.  Defaults to 15 minutes
            if not provided.

    Returns:
        An encoded JWT string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT refresh token.

    The token carries an extra ``"type": "refresh"`` claim that the
    ``refresh_access_token`` validator checks to prevent access tokens being
    passed to the refresh endpoint.

    Args:
        data: Claims to include (typically ``{"sub": username}``).
        expires_delta: Token lifetime.  Defaults to 7 days.

    Returns:
        An encoded JWT string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency that decodes the Bearer token and returns the active user.

    Args:
        token: JWT access token extracted from the ``Authorization`` header.
        db: Database session injected by FastAPI.

    Returns:
        The authenticated ``User`` ORM object.

    Raises:
        HTTPException: 401 if the token is missing, expired, invalid, or the
            user no longer exists in the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency that requires the requesting user to be an admin.

    Args:
        current_user: The authenticated user resolved by ``get_current_user``.

    Returns:
        The same ``User`` object, guaranteed to have ``is_admin=True``.

    Raises:
        HTTPException: 403 if the user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    Validate a refresh token and return the subject claim if valid.

    The ``"type": "refresh"`` claim is checked to ensure access tokens cannot
    be misused as refresh tokens.

    Args:
        refresh_token: The JWT refresh token string provided by the client.
        db: Database session injected by FastAPI.

    Returns:
        A dict ``{"sub": username}`` suitable for passing to
        ``create_access_token``.

    Raises:
        HTTPException: 401 if the token is invalid, expired, the wrong type,
            or the user no longer exists.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Reject the token if it is not a refresh token
        if payload.get("type") != "refresh":
            raise credentials_exception
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return {"sub": username}
