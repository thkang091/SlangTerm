from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import SlangTerm, SlangVote, User
from schemas import VoteCreate, VoteResponse, StatsResponse, SlangTermResponse
from auth import get_current_user

router = APIRouter(
    prefix="/community",
    tags=["community"]
)

@router.post("/vote", response_model=VoteResponse)
async def vote_on_slang(
    vote: VoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Vote on a slang term (upvote, downvote, or remove vote)"""
    # Check if slang term exists and is verified
    slang_term = db.query(SlangTerm).filter(SlangTerm.id == vote.slang_id).first()
    if not slang_term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slang term with ID {vote.slang_id} not found"
        )
    
    if not slang_term.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot vote on unverified slang terms"
        )
    
    # Check existing vote
    existing_vote = (
        db.query(SlangVote)
        .filter(
            SlangVote.slang_id == vote.slang_id,
            SlangVote.user_id == current_user.id
        )
        .first()
    )
    
    if existing_vote:
        if vote.vote == 0:
            # Remove vote
            db.delete(existing_vote)
            db.commit()
            return VoteResponse(
                id=0,
                slang_id=vote.slang_id,
                vote=0,
                created_at=None
            )
        else:
            # Update vote
            existing_vote.vote = vote.vote
            db.commit()
            db.refresh(existing_vote)
            return VoteResponse.from_orm(existing_vote)
    else:
        if vote.vote == 0:
            # No-op if trying to remove a non-existent vote
            return VoteResponse(
                id=0,
                slang_id=vote.slang_id,
                vote=0,
                created_at=None
            )
        
        # Create new vote
        new_vote = SlangVote(
            slang_id=vote.slang_id,
            user_id=current_user.id,
            vote=vote.vote
        )
        db.add(new_vote)
        db.commit()
        db.refresh(new_vote)
        
        return VoteResponse.from_orm(new_vote)

@router.get("/stats", response_model=StatsResponse)
async def get_community_stats(
    db: Session = Depends(get_db)
):
    """Get community statistics"""
    # Count total terms
    total_terms = db.query(func.count(SlangTerm.id)).scalar()
    
    # Count verified terms
    verified_terms = db.query(func.count(SlangTerm.id)).filter(SlangTerm.is_verified == True).scalar()
    
    # Count pending terms
    pending_terms = db.query(func.count(SlangTerm.id)).filter(SlangTerm.is_verified == False).scalar()
    
    # Get recent submissions (last 10)
    recent_submissions = (
        db.query(SlangTerm)
        .filter(SlangTerm.is_verified == True)
        .order_by(SlangTerm.created_at.desc())
        .limit(10)
        .all()
    )
    
    # Get popular terms (most votes)
    popular_subquery = (
        db.query(
            SlangTerm.id,
            func.count(SlangVote.id).label("vote_count")
        )
        .join(SlangVote)
        .filter(SlangTerm.is_verified == True)
        .group_by(SlangTerm.id)
        .order_by(func.count(SlangVote.id).desc())
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

@router.get("/my-votes")
async def get_user_votes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's votes"""
    user_votes = (
        db.query(SlangVote)
        .filter(SlangVote.user_id == current_user.id)
        .all()
    )
    
    # Format as dictionary for easy lookup
    vote_map = {vote.slang_id: vote.vote for vote in user_votes}
    
    return vote_map