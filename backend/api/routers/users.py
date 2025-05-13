"""
API endpoints for user data and authentication.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ...models.database import get_db
from ...models.user import User, NotificationSetting, Team
from ...models.player import Player
from ...utils.config import settings
from ...utils.errors import AuthenticationError, AuthorizationError, ResourceNotFoundError

router = APIRouter()

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT settings
SECRET_KEY = "temporary_secret_key"  # In production, use a secure key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Pydantic models for request/response
class UserCreate(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    password: str
    email_notifications: bool = True
    push_notifications: bool = False
    web_notifications: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    web_notifications: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class NotificationSettingCreate(BaseModel):
    player_id: Optional[int] = None
    team: Optional[str] = None
    email_enabled: bool = True
    push_enabled: bool = True
    web_enabled: bool = True
    min_importance: int = Field(3, ge=1, le=5)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


# Helper functions
def verify_password(plain_password, hashed_password):
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Generate a password hash."""
    return pwd_context.hash(password)


def authenticate_user(db: Session, email: str, password: str):
    """Authenticate a user."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user


# Routes
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Get an access token for authentication.
    
    Args:
        form_data: OAuth2 password request form.
        db: Database session.
    
    Returns:
        Access token.
    
    Raises:
        HTTPException: If authentication fails.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    Args:
        user_data: User registration data.
        db: Database session.
    
    Returns:
        The created user.
    
    Raises:
        HTTPException: If the email is already registered.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        email_notifications=user_data.email_notifications,
        push_notifications=user_data.push_notifications,
        web_notifications=user_data.web_notifications,
        is_active=True,
        is_verified=False  # Require email verification
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "username": new_user.username,
        "is_active": new_user.is_active,
        "is_verified": new_user.is_verified
    }


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get information about the current user.
    
    Args:
        current_user: The authenticated user.
    
    Returns:
        User information.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "email_notifications": current_user.email_notifications,
        "push_notifications": current_user.push_notifications,
        "web_notifications": current_user.web_notifications,
        "quiet_hours_start": current_user.quiet_hours_start,
        "quiet_hours_end": current_user.quiet_hours_end,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified
    }


@router.put("/me")
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's information.
    
    Args:
        user_data: User update data.
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        Updated user information.
    """
    # Update user fields
    if user_data.username is not None:
        current_user.username = user_data.username
    
    if user_data.email_notifications is not None:
        current_user.email_notifications = user_data.email_notifications
    
    if user_data.push_notifications is not None:
        current_user.push_notifications = user_data.push_notifications
    
    if user_data.web_notifications is not None:
        current_user.web_notifications = user_data.web_notifications
    
    if user_data.quiet_hours_start is not None:
        current_user.quiet_hours_start = user_data.quiet_hours_start
    
    if user_data.quiet_hours_end is not None:
        current_user.quiet_hours_end = user_data.quiet_hours_end
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "email_notifications": current_user.email_notifications,
        "push_notifications": current_user.push_notifications,
        "web_notifications": current_user.web_notifications,
        "quiet_hours_start": current_user.quiet_hours_start,
        "quiet_hours_end": current_user.quiet_hours_end,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified
    }


@router.get("/me/favorites/teams")
async def get_favorite_teams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's favorite teams.
    
    Args:
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        List of favorite teams.
    """
    # Refresh the user to get the latest favorites
    db.refresh(current_user)
    
    return {
        "teams": [
            {
                "name": team.name,
                "abbreviation": team.abbreviation,
                "city": team.city,
                "conference": team.conference,
                "division": team.division
            }
            for team in current_user.favorite_teams
        ]
    }


@router.post("/me/favorites/teams/{team_abbreviation}")
async def add_favorite_team(
    team_abbreviation: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a team to the current user's favorites.
    
    Args:
        team_abbreviation: Abbreviation of the team to add.
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        Success message.
    
    Raises:
        HTTPException: If the team is not found.
    """
    # Find the team
    team = db.query(Team).filter(Team.abbreviation == team_abbreviation).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with abbreviation {team_abbreviation} not found"
        )
    
    # Add to favorites if not already there
    if team not in current_user.favorite_teams:
        current_user.favorite_teams.append(team)
        db.commit()
    
    return {"message": f"Team {team.name} added to favorites"}


@router.delete("/me/favorites/teams/{team_abbreviation}")
async def remove_favorite_team(
    team_abbreviation: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a team from the current user's favorites.
    
    Args:
        team_abbreviation: Abbreviation of the team to remove.
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        Success message.
    """
    # Find the team
    team = db.query(Team).filter(Team.abbreviation == team_abbreviation).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with abbreviation {team_abbreviation} not found"
        )
    
    # Remove from favorites if present
    if team in current_user.favorite_teams:
        current_user.favorite_teams.remove(team)
        db.commit()
    
    return {"message": f"Team {team.name} removed from favorites"}


@router.get("/me/favorites/players")
async def get_favorite_players(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's favorite players.
    
    Args:
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        List of favorite players.
    """
    # Refresh the user to get the latest favorites
    db.refresh(current_user)
    
    return {
        "players": [
            {
                "id": player.id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "jersey_number": player.jersey_number,
                "current_rank": player.current_rank,
                "is_top_100": player.is_top_100
            }
            for player in current_user.favorite_players
        ]
    }


@router.post("/me/favorites/players/{player_id}")
async def add_favorite_player(
    player_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a player to the current user's favorites.
    
    Args:
        player_id: ID of the player to add.
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        Success message.
    
    Raises:
        HTTPException: If the player is not found.
    """
    # Find the player
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with ID {player_id} not found"
        )
    
    # Add to favorites if not already there
    if player not in current_user.favorite_players:
        current_user.favorite_players.append(player)
        db.commit()
    
    return {"message": f"Player {player.name} added to favorites"}


@router.delete("/me/favorites/players/{player_id}")
async def remove_favorite_player(
    player_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a player from the current user's favorites.
    
    Args:
        player_id: ID of the player to remove.
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        Success message.
    """
    # Find the player
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with ID {player_id} not found"
        )
    
    # Remove from favorites if present
    if player in current_user.favorite_players:
        current_user.favorite_players.remove(player)
        db.commit()
    
    return {"message": f"Player {player.name} removed from favorites"}


@router.get("/me/notification-settings")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's notification settings.
    
    Args:
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        List of notification settings.
    """
    # Refresh the user to get the latest settings
    db.refresh(current_user)
    
    return {
        "settings": [
            {
                "id": setting.id,
                "player_id": setting.player_id,
                "player_name": setting.player.name if setting.player_id else None,
                "team": setting.team,
                "email_enabled": setting.email_enabled,
                "push_enabled": setting.push_enabled,
                "web_enabled": setting.web_enabled,
                "min_importance": setting.min_importance
            }
            for setting in current_user.notification_settings
        ]
    }


@router.post("/me/notification-settings")
async def create_notification_setting(
    setting_data: NotificationSettingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new notification setting for the current user.
    
    Args:
        setting_data: Notification setting data.
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        The created notification setting.
    
    Raises:
        HTTPException: If the player or team is not found, or if a setting already exists.
    """
    # Validate that either player_id or team is provided
    if setting_data.player_id is None and setting_data.team is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either player_id or team must be provided"
        )
    
    # Check if a setting already exists for this player/team
    existing_setting = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id,
        or_(
            and_(
                NotificationSetting.player_id == setting_data.player_id,
                setting_data.player_id is not None
            ),
            and_(
                NotificationSetting.team == setting_data.team,
                setting_data.team is not None
            )
        )
    ).first()
    
    if existing_setting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A notification setting already exists for this player or team"
        )
    
    # Validate player_id if provided
    if setting_data.player_id is not None:
        player = db.query(Player).filter(Player.id == setting_data.player_id).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {setting_data.player_id} not found"
            )
    
    # Create the notification setting
    new_setting = NotificationSetting(
        user_id=current_user.id,
        player_id=setting_data.player_id,
        team=setting_data.team,
        email_enabled=setting_data.email_enabled,
        push_enabled=setting_data.push_enabled,
        web_enabled=setting_data.web_enabled,
        min_importance=setting_data.min_importance
    )
    
    db.add(new_setting)
    db.commit()
    db.refresh(new_setting)
    
    return {
        "id": new_setting.id,
        "player_id": new_setting.player_id,
        "player_name": new_setting.player.name if new_setting.player_id else None,
        "team": new_setting.team,
        "email_enabled": new_setting.email_enabled,
        "push_enabled": new_setting.push_enabled,
        "web_enabled": new_setting.web_enabled,
        "min_importance": new_setting.min_importance
    }


@router.delete("/me/notification-settings/{setting_id}")
async def delete_notification_setting(
    setting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a notification setting.
    
    Args:
        setting_id: ID of the notification setting to delete.
        current_user: The authenticated user.
        db: Database session.
    
    Returns:
        Success message.
    
    Raises:
        HTTPException: If the setting is not found or doesn't belong to the user.
    """
    # Find the setting
    setting = db.query(NotificationSetting).filter(
        NotificationSetting.id == setting_id,
        NotificationSetting.user_id == current_user.id
    ).first()
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification setting with ID {setting_id} not found or doesn't belong to you"
        )
    
    # Delete the setting
    db.delete(setting)
    db.commit()
    
    return {"message": f"Notification setting with ID {setting_id} deleted"}
