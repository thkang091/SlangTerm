from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import User, SlangTerm, user_favorites, SearchHistory
from schemas import UserResponse, UserCreate, SlangTermResponse, FavoriteToggle
from auth import get_current_user, get_admin_user

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    # Validate username uniqueness if changed
    if user_update.username and user_update.username != current_user.username:
        existing_user = db.query(User).filter(User.username == user_update.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
    
    # Update user fields
    current_user.username = user_update.username
    current_user.native_language = user_update.native_language
    current_user.learning_languages = user_update.learning_languages or []
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/favorites", response_model=List[SlangTermResponse])
async def get_favorites(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's favorite slang terms"""
    # Query favorites with pagination
    favorites = (
        db.query(SlangTerm)
        .join(user_favorites)
        .filter(user_favorites.c.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Add vote counts to each term
    results = []
    for term in favorites:
        vote_count = (
            db.query(SlangTerm.votes)
            .filter(SlangTerm.votes.slang_id == term.id)
            .with_entities(SlangTerm.votes.vote)
            .scalar() or 0
        )
        term_response = SlangTermResponse.from_orm(term)
        term_response.vote_count = vote_count
        results.append(term_response)
    
    return results

@router.post("/favorites", status_code=status.HTTP_200_OK)
async def toggle_favorite(
    favorite: FavoriteToggle,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add or remove a slang term from favorites"""
    # Check if term exists
    term = db.query(SlangTerm).filter(SlangTerm.id == favorite.slang_id).first()
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slang term with ID {favorite.slang_id} not found"
        )
    
    # Check if already in favorites
    is_favorite = (
        db.query(user_favorites)
        .filter(
            user_favorites.c.user_id == current_user.id,
            user_favorites.c.slang_id == favorite.slang_id
        )
        .first() is not None
    )
    
    # Toggle favorite status
    if is_favorite:
        # Remove from favorites
        db.execute(
            user_favorites.delete().where(
                user_favorites.c.user_id == current_user.id,
                user_favorites.c.slang_id == favorite.slang_id
            )
        )
        action = "removed"
    else:
        # Add to favorites
        db.execute(
            user_favorites.insert().values(
                user_id=current_user.id,
                slang_id=favorite.slang_id
            )
        )
        action = "added"
    
    db.commit()
    
    return {"status": "success", "action": action, "slang_id": favorite.slang_id}

@router.get("/submissions", response_model=List[SlangTermResponse])
async def get_user_submissions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get slang terms submitted by the current user"""
    # Query submissions with pagination
    submissions = (
        db.query(SlangTerm)
        .filter(SlangTerm.submitted_by == current_user.id)
        .order_by(SlangTerm.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Add vote counts to each term
    results = []
    for term in submissions:
        vote_count = db.query(SlangTerm.votes).filter(SlangTerm.votes.slang_id == term.id).count() or 0
        term_response = SlangTermResponse.from_orm(term)
        term_response.vote_count = vote_count
        results.append(term_response)
    
    return results

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)  # Only admins can view other user profiles
):
    """Get user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return user

@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    role: str = Query(..., description="New role (user, moderator, admin)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)  # Only admins can update roles
):
    """Update user role (admin only)"""
    # Validate role
    if role not in ["user", "moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'user', 'moderator', or 'admin'."
        )
    
    # Get user to update
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Update role
    user.role = role
    db.commit()
    db.refresh(user)
    
    return user