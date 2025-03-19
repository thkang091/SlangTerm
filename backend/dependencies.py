from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import datetime
from typing import Optional
from database import get_db
from models import User, SlangTerm
from config import MAX_SUBMISSIONS_PER_DAY
from embeddings import embedding_service
from auth import get_current_user

async def get_embedding_service():
    """Dependency for the embedding service"""
    return embedding_service

async def check_submission_limit(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check if user has exceeded the daily submission limit"""
    # Check if user is admin or moderator (no limits)
    if user.role in ["admin", "moderator"]:
        return user
    
    # Get the start of today
    today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Count submissions made today
    today_submissions = (
        db.query(SlangTerm)
        .filter(
            SlangTerm.submitted_by == user.id,
            SlangTerm.created_at >= today_start
        )
        .count()
    )
    
    if today_submissions >= MAX_SUBMISSIONS_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You have reached the daily submission limit of {MAX_SUBMISSIONS_PER_DAY} terms."
        )
    
    return user

async def get_slang_term(slang_id: int, db: Session = Depends(get_db)) -> SlangTerm:
    """Get a slang term by ID or raise 404"""
    slang_term = db.query(SlangTerm).filter(SlangTerm.id == slang_id).first()
    
    if not slang_term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slang term with ID {slang_id} not found"
        )
    
    return slang_term

async def check_slang_owner(
    slang_term: SlangTerm = Depends(get_slang_term),
    current_user: User = Depends(get_current_user)
):
    """Check if current user is the owner of the slang term or has admin rights"""
    if current_user.role in ["admin", "moderator"]:
        return slang_term
    
    if slang_term.submitted_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action on this slang term"
        )
    
    return slang_term

async def initialize_index(db: Session = Depends(get_db)):
    """Ensure the FAISS index is initialized"""
    if embedding_service.index is None:
        embedding_service.build_index(db)
    return embedding_service