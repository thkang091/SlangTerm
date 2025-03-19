from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
import json
import datetime

from database import get_db
from models import SlangTerm, User, SlangVote
from schemas import SlangTermResponse, ModerateRequest, StatsResponse
from auth import get_moderator_user
from dependencies import get_slang_term, initialize_index
from ai_service import ai_service
from embeddings import embedding_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.get("/pending", response_model=List[SlangTermResponse])
async def get_pending_submissions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user)
):
    """Get pending slang term submissions for moderation"""
    # Query unverified terms
    pending_terms = (
        db.query(SlangTerm)
        .filter(SlangTerm.is_verified == False)
        .order_by(desc(SlangTerm.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Add vote counts to each term
    results = []
    for term in pending_terms:
        vote_count = (
            db.query(func.sum(SlangVote.vote))
            .filter(SlangVote.slang_id == term.id)
            .scalar() or 0
        )
        term_response = SlangTermResponse.from_orm(term)
        term_response.vote_count = vote_count
        results.append(term_response)
    
    return results

@router.post("/moderate/{slang_id}", response_model=SlangTermResponse)
async def moderate_submission(
    moderate_request: ModerateRequest,
    slang_term: SlangTerm = Depends(get_slang_term),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user)
):
    """Moderate a slang term submission (approve, reject, update)"""
    if moderate_request.action == "approve":
        # Approve the submission
        slang_term.is_verified = True
        db.commit()
        db.refresh(slang_term)
        
        # Rebuild the search index
        embedding_service.build_index(db)
        
    elif moderate_request.action == "reject":
        # Delete the submission
        db.delete(slang_term)
        db.commit()
        
        # Return empty response since term is deleted
        return SlangTermResponse(
            id=moderate_request.slang_id,
            term="",
            meaning="",
            created_at=datetime.datetime.now(),
            is_verified=False,
            vote_count=0
        )
        
    elif moderate_request.action == "update":
        if not moderate_request.updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Updates are required for 'update' action"
            )
        
        # Update term fields
        slang_term.term = moderate_request.updates.term
        slang_term.meaning = moderate_request.updates.meaning
        slang_term.origin = moderate_request.updates.origin
        slang_term.context = moderate_request.updates.context
        slang_term.part_of_speech = moderate_request.updates.part_of_speech
        slang_term.pronunciation = moderate_request.updates.pronunciation
        slang_term.alternative_spellings = moderate_request.updates.alternative_spellings or []
        slang_term.examples = moderate_request.updates.examples or []
        slang_term.is_verified = True  # Auto-verify after update
        
        # Update embedding
        text_to_embed = f"{slang_term.term} {slang_term.meaning}"
        if slang_term.examples:
            text_to_embed += " " + " ".join(slang_term.examples[:2])
        slang_term.embedding = embedding_service.get_embedding(text_to_embed)
        
        db.commit()
        db.refresh(slang_term)
        
        # Rebuild the search index
        embedding_service.build_index(db)
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve', 'reject', or 'update'."
        )
    
    # Get vote count for response
    vote_count = (
        db.query(func.sum(SlangVote.vote))
        .filter(SlangVote.slang_id == slang_term.id)
        .scalar() or 0
    )
    
    # Build response
    response = SlangTermResponse.from_orm(slang_term)
    response.vote_count = vote_count
    
    return response

@router.post("/ai-moderate/{slang_id}")
async def ai_moderate_submission(
    slang_term: SlangTerm = Depends(get_slang_term),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user)
):
    """Use AI to help moderate a slang term submission"""
    # Get examples as list
    examples = slang_term.examples or []
    
    # Call AI moderation service
    moderation_result = await ai_service.moderate_submission(
        slang_term.term,
        slang_term.meaning,
        examples
    )
    
    # Parse the JSON response if it's a string
    if isinstance(moderation_result, str):
        moderation = json.loads(moderation_result)
    else:
        moderation = moderation_result
    
    return moderation

@router.get("/stats", response_model=StatsResponse)
async def get_admin_stats(
    days: int = Query(30, description="Stats for the last N days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user)
):
    """Get detailed statistics for admin dashboard"""
    # Define the date range
    recent_date = datetime.datetime.now() - datetime.timedelta(days=days)
    
    # Count total terms
    total_terms = db.query(func.count(SlangTerm.id)).scalar()
    
    # Count verified terms
    verified_terms = db.query(func.count(SlangTerm.id)).filter(SlangTerm.is_verified == True).scalar()
    
    # Count pending terms
    pending_terms = db.query(func.count(SlangTerm.id)).filter(SlangTerm.is_verified == False).scalar()
    
    # Get recent submissions
    recent_submissions = (
        db.query(SlangTerm)
        .filter(SlangTerm.created_at >= recent_date)
        .order_by(SlangTerm.created_at.desc())
        .limit(10)
        .all()
    )
    
    # Get popular terms (most votes)
    popular_subquery = (
        db.query(
            SlangTerm.id,
            func.sum(SlangVote.vote).label("vote_count")
        )
        .join(SlangVote)
        .group_by(SlangTerm.id)
        .order_by(func.sum(SlangVote.vote).desc())
        .limit(10)
        .subquery()
    )
    
    popular_terms = (
        db.query(SlangTerm)
        .join(popular_subquery, SlangTerm.id == popular_subquery.c.id)
        .all()
    )
    
    # Format response with vote counts
    recent_with_votes = []
    for term in recent_submissions:
        vote_count = (
            db.query(func.sum(SlangVote.vote))
            .filter(SlangVote.slang_id == term.id)
            .scalar() or 0
        )
        term_response = SlangTermResponse.from_orm(term)
        term_response.vote_count = vote_count
        recent_with_votes.append(term_response)
    
    popular_with_votes = []
    for term in popular_terms:
        vote_count = (
            db.query(func.sum(SlangVote.vote))
            .filter(SlangVote.slang_id == term.id)
            .scalar() or 0
        )
        term_response = SlangTermResponse.from_orm(term)
        term_response.vote_count = vote_count
        popular_with_votes.append(term_response)
    
    return StatsResponse(
        total_terms=total_terms,
        verified_terms=verified_terms,
        pending_terms=pending_terms,
        recent_submissions=recent_with_votes,
        popular_terms=popular_with_votes
    )

@router.post("/rebuild-index", status_code=status.HTTP_200_OK)
async def rebuild_search_index(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user)
):
    """Manually rebuild the search index (admin only)"""
    embedding_service.build_index(db)
    return {"status": "success", "message": "Search index rebuilt successfully"}