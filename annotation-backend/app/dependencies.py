"""
Reusable FastAPI dependency functions shared across API routers.

These are injected via ``Depends(...)`` and handle cross-cutting concerns
such as database session management and access-control checks.
"""
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .database import SessionLocal
from .config import get_settings
from .models import User, ProjectAssignment

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_db() -> Generator:
    """
    FastAPI dependency that provides a request-scoped database session.

    Opens a ``SessionLocal`` session and closes it after the request
    finishes, even if an exception was raised.

    Yields:
        Session: An active SQLAlchemy ORM session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    FastAPI dependency that decodes the Bearer token and returns the active user.

    Args:
        db: Database session.
        token: JWT access token from the ``Authorization`` header.

    Returns:
        The authenticated ``User`` ORM object.

    Raises:
        HTTPException: 401 if the token is invalid or the user no longer exists.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM]
        )
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
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency that requires the requesting user to be an admin.

    Args:
        current_user: Authenticated user resolved by ``get_current_user``.

    Returns:
        The same ``User`` object, guaranteed to have ``is_admin=True``.

    Raises:
        HTTPException: 403 if the user does not have admin privileges.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


async def verify_project_access(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Dependency to verify if the current user has access to the project.

    Admins are granted access to every project unconditionally.  Regular
    users must have a ``ProjectAssignment`` row linking their account to the
    requested project.

    Args:
        project_id: The project being accessed, taken from the route path.
        db: Database session.
        current_user: The authenticated user.

    Raises:
        HTTPException: 403 if the non-admin user is not assigned to the project.
    """
    if current_user.is_admin:
        # Admins have access to all projects
        return

    # Check if the user is assigned to the project
    assignment = db.query(ProjectAssignment).filter(
        ProjectAssignment.user_id == current_user.id,
        ProjectAssignment.project_id == project_id
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project"
        )
    # If assignment exists, user has access
    return
