from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
import datetime

from database import get_db
from models import SlangTerm, User, SearchHistory
from schemas import SearchQuery, SearchResponse, SlangTermResponse
from auth import get_current_user
from dependencies import initialize_index
from embeddings import EmbeddingService

router = APIRouter(
    prefix="/search",
    tags=["search"]
)

@router.post("/", response_model=SearchResponse)
async def search_slang_terms(
    search_query: SearchQuery,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    embedding_service: EmbeddingService = Depends(initialize_index)
):
    """Search for slang terms using keyword or semantic search"""
    query = search_query.query.strip()
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )
    
    # Save search to history
    if current_user:
        search_history = SearchHistory(
            user_id=current_user.id,
            query=query
        )
        db.add(search_history)
        db.commit()
    
    results = []
    
    # Perform semantic search if enabled
    if search_query.semantic:
        # Get similar terms using vector search
        semantic_results = embedding_service.search(query, search_query.limit)
        
        if semantic_results:
            # Get slang terms by IDs with vote counts
            slang_ids = [result["slang_id"] for result in semantic_results]
            
            # Query database for these terms
            terms_query = (
                db.query(SlangTerm)
                .filter(SlangTerm.id.in_(slang_ids))
                .filter(SlangTerm.is_verified == True)
            )
            
            # Preserve the order from semantic search
            id_to_position = {id: idx for idx, id in enumerate(slang_ids)}
            terms = terms_query.all()
            terms.sort(key=lambda x: id_to_position.get(x.id, 999))
            
            # Build response with vote counts
            for term in terms:
                vote_count = (
                    db.query(func.coalesce(func.sum(SlangTerm.votes.vote), 0))
                    .filter(SlangTerm.id == term.id)
                    .scalar() or 0
                )
                term_response = SlangTermResponse.from_orm(term)
                term_response.vote_count = vote_count
                results.append(term_response)
    
    # Fall back to keyword search if no semantic results or semantic search is disabled
    if not results:
        # Perform keyword search
        keyword_query = (
            db.query(SlangTerm)
            .filter(
                SlangTerm.is_verified == True,
                or_(
                    func.lower(SlangTerm.term).contains(query.lower()),
                    func.lower(SlangTerm.meaning).contains(query.lower())
                )
            )
            .limit(search_query.limit)
        )
        
        terms = keyword_query.all()
        
        # Build response with vote counts
        for term in terms:
            vote_count = (
                db.query(func.coalesce(func.sum(SlangTerm.votes.vote), 0))
                .filter(SlangTerm.id == term.id)
                .scalar() or 0
            )
            term_response = SlangTermResponse.from_orm(term)
            term_response.vote_count = vote_count
            results.append(term_response)
    
    return SearchResponse(
        results=results,
        query=query,
        count=len(results)
    )

@router.get("/trending", response_model=List[SlangTermResponse])
async def get_trending_terms(
    limit: int = Query(10, ge=1, le=100),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get trending slang terms based on recent activity"""
    # Define the date range for trending
    recent_date = datetime.datetime.now() - datetime.timedelta(days=days)
    
    # Get terms with the most votes in the recent period
    recent_votes_subquery = (
        db.query(
            SlangTerm.id,
            func.count().label("vote_count")
        )
        .join(SlangTerm.votes)
        .filter(
            SlangTerm.is_verified == True,
            SlangTerm.votes.created_at >= recent_date
        )
        .group_by(SlangTerm.id)
        .subquery()
    )
    
    # Get terms with the most searches in the recent period
    search_counts = {}
    recent_searches = (
        db.query(SearchHistory.query, func.count().label("count"))
        .filter(SearchHistory.created_at >= recent_date)
        .group_by(SearchHistory.query)
        .order_by(func.count().desc())
        .limit(100)
        .all()
    )
    
    # Count how many times each term appears in searches
    for search_query, count in recent_searches:
        for term in db.query(SlangTerm).filter(
            SlangTerm.is_verified == True,
            func.lower(SlangTerm.term).contains(func.lower(search_query))
        ).all():
            search_counts[term.id] = search_counts.get(term.id, 0) + count
    
    # Combine vote counts and search counts for trending score
    trending_scores = {}
    
    # Add vote-based scores
    for term_id, vote_count in db.query(recent_votes_subquery).all():
        trending_scores[term_id] = trending_scores.get(term_id, 0) + vote_count * 2  # Weight votes higher
    
    # Add search-based scores
    for term_id, search_count in search_counts.items():
        trending_scores[term_id] = trending_scores.get(term_id, 0) + search_count
    
    # Get top trending terms
    top_trending_ids = sorted(
        trending_scores.keys(),
        key=lambda id: trending_scores[id],
        reverse=True
    )[:limit]
    
    # Query full term details and vote counts
    results = []
    if top_trending_ids:
        terms = (
            db.query(SlangTerm)
            .filter(SlangTerm.id.in_(top_trending_ids))
            .all()
        )
        
        # Sort by trending score and add vote counts
        terms.sort(key=lambda term: trending_scores.get(term.id, 0), reverse=True)
        
        for term in terms:
            vote_count = (
                db.query(func.coalesce(func.sum(SlangTerm.votes.vote), 0))
                .filter(SlangTerm.id == term.id)
                .scalar() or 0
            )
            term_response = SlangTermResponse.from_orm(term)
            term_response.vote_count = vote_count
            results.append(term_response)
    
    return results

@router.get("/popular", response_model=List[SlangTermResponse])
async def get_popular_terms(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get most popular slang terms based on all-time votes"""
    # Subquery to get vote counts
    vote_counts = (
        db.query(
            SlangTerm.id,
            func.coalesce(func.sum(SlangTerm.votes.vote), 0).label("vote_count")
        )
        .outerjoin(SlangTerm.votes)
        .filter(SlangTerm.is_verified == True)
        .group_by(SlangTerm.id)
        .order_by(func.coalesce(func.sum(SlangTerm.votes.vote), 0).desc())
        .limit(limit)
        .subquery()
    )
    
    # Get terms with vote counts
    terms = (
        db.query(SlangTerm, vote_counts.c.vote_count)
        .join(vote_counts, SlangTerm.id == vote_counts.c.id)
        .order_by(vote_counts.c.vote_count.desc())
        .all()
    )
    
    # Build response
    results = []
    for term, vote_count in terms:
        term_response = SlangTermResponse.from_orm(term)
        term_response.vote_count = vote_count
        results.append(term_response)
    
    return results

@router.get("/history", response_model=List[str])
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's search history"""
    history = (
        db.query(SearchHistory.query)
        .filter(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    
    return [item[0] for item in history]

@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_search_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear user's search history"""
    db.query(SearchHistory).filter(SearchHistory.user_id == current_user.id).delete()
    db.commit()
    
    return None