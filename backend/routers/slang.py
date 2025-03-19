from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional
import json

from database import get_db
from models import SlangTerm, SlangVote, User, SlangTranslation
from schemas import (
    SlangTermCreate, 
    SlangTermResponse, 
    SlangTermDetail,
    TranslationCreate,
    TranslationResponse
)
from auth import get_current_user, get_moderator_user
from dependencies import get_slang_term, check_submission_limit, check_slang_owner, get_embedding_service
from ai_service import ai_service
from embeddings import embedding_service

router = APIRouter(
    prefix="/slang",
    tags=["slang"]
)

@router.post("/", response_model=SlangTermResponse, status_code=status.HTTP_201_CREATED)
async def create_slang_term(
    slang_term: SlangTermCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_submission_limit)
):
    """Create a new slang term"""
    
    # Check if the term already exists
    existing_term = db.query(SlangTerm).filter(func.lower(SlangTerm.term) == func.lower(slang_term.term)).first()
    if existing_term:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slang term '{slang_term.term}' already exists"
        )
    
    # Auto-verify submissions from moderators and admins
    is_verified = current_user.role in ["admin", "moderator"]
    
    # Convert lists to JSON strings for storage
    alternative_spellings = slang_term.alternative_spellings or []
    examples = slang_term.examples or []
    
    # Create embedding for the term
    text_to_embed = f"{slang_term.term} {slang_term.meaning}"
    if examples:
        text_to_embed += " " + " ".join(examples[:2])
    embedding = embedding_service.get_embedding(text_to_embed)
    
    # Create new slang term
    new_slang = SlangTerm(
        term=slang_term.term,
        meaning=slang_term.meaning,
        origin=slang_term.origin,
        context=slang_term.context,
        part_of_speech=slang_term.part_of_speech,
        pronunciation=slang_term.pronunciation,
        alternative_spellings=alternative_spellings,
        examples=examples,
        is_verified=is_verified,
        submitted_by=current_user.id,
        embedding=embedding
    )
    
    db.add(new_slang)
    db.commit()
    db.refresh(new_slang)
    
    # Add initial upvote from submitter
    vote = SlangVote(
        slang_id=new_slang.id,
        user_id=current_user.id,
        vote=1
    )
    db.add(vote)
    db.commit()
    
    # Rebuild the search index to include the new term
    if is_verified:
        embedding_service.build_index(db)
    
    # Add vote count to response
    response = SlangTermResponse.from_orm(new_slang)
    response.vote_count = 1
    
    return response

@router.get("/", response_model=List[SlangTermResponse])
async def get_slang_terms(
    skip: int = 0,
    limit: int = 100,
    verified_only: bool = True,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get all slang terms with pagination"""
    query = db.query(SlangTerm)
    
    # Filter by verification status unless user is moderator/admin
    if verified_only and current_user.role not in ["admin", "moderator"]:
        query = query.filter(SlangTerm.is_verified == True)
    
    # Get total votes for each term
    terms = query.order_by(desc(SlangTerm.created_at)).offset(skip).limit(limit).all()
    
    # Add vote count to each term
    result = []
    for term in terms:
        term_dict = SlangTermResponse.from_orm(term)
        term_dict.vote_count = db.query(func.sum(SlangVote.vote)).filter(SlangVote.slang_id == term.id).scalar() or 0
        result.append(term_dict)
    
    return result

@router.get("/{slang_id}", response_model=SlangTermDetail)
async def get_slang_term_by_id(
    slang_term: SlangTerm = Depends(get_slang_term),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get a specific slang term by ID"""
    # Check if term is verified or user is admin/moderator
    if not slang_term.is_verified and current_user.role not in ["admin", "moderator"]:
        # Allow the submitter to see their own unverified submissions
        if slang_term.submitted_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this unverified slang term"
            )
    
    # Get vote count
    vote_count = db.query(func.sum(SlangVote.vote)).filter(SlangVote.slang_id == slang_term.id).scalar() or 0
    
    # Get translations
    translations = db.query(SlangTranslation).filter(SlangTranslation.slang_id == slang_term.id).all()
    
    # Build response
    response = SlangTermDetail.from_orm(slang_term)
    response.vote_count = vote_count
    response.translations = [TranslationResponse.from_orm(t) for t in translations]
    
    return response

@router.put("/{slang_id}", response_model=SlangTermResponse)
async def update_slang_term(
    slang_update: SlangTermCreate,
    slang_term: SlangTerm = Depends(check_slang_owner),
    db: Session = Depends(get_db)
):
    """Update a slang term (only by owner or moderator)"""
    # Update the term fields
    slang_term.term = slang_update.term
    slang_term.meaning = slang_update.meaning
    slang_term.origin = slang_update.origin
    slang_term.context = slang_update.context
    slang_term.part_of_speech = slang_update.part_of_speech
    slang_term.pronunciation = slang_update.pronunciation
    slang_term.alternative_spellings = slang_update.alternative_spellings or []
    slang_term.examples = slang_update.examples or []
    
    # If user is not a moderator/admin, mark as unverified after update
    current_user = slang_term.submitter
    if current_user.role not in ["admin", "moderator"]:
        slang_term.is_verified = False
    
    # Update embedding
    text_to_embed = f"{slang_term.term} {slang_term.meaning}"
    if slang_term.examples:
        text_to_embed += " " + " ".join(slang_term.examples[:2])
    slang_term.embedding = embedding_service.get_embedding(text_to_embed)
    
    db.commit()
    db.refresh(slang_term)
    
    # Rebuild index if term is verified
    if slang_term.is_verified:
        embedding_service.build_index(db)
    
    # Get vote count
    vote_count = db.query(func.sum(SlangVote.vote)).filter(SlangVote.slang_id == slang_term.id).scalar() or 0
    
    # Build response
    response = SlangTermResponse.from_orm(slang_term)
    response.vote_count = vote_count
    
    return response

@router.delete("/{slang_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slang_term(
    slang_term: SlangTerm = Depends(check_slang_owner),
    db: Session = Depends(get_db)
):
    """Delete a slang term (only by owner or moderator)"""
    # Delete associated votes and translations first
    db.query(SlangVote).filter(SlangVote.slang_id == slang_term.id).delete()
    db.query(SlangTranslation).filter(SlangTranslation.slang_id == slang_term.id).delete()
    
    # Then delete the term
    db.delete(slang_term)
    db.commit()
    
    # Rebuild index
    embedding_service.build_index(db)
    
    return None

@router.post("/generate-explanation", response_model=SlangTermCreate)
async def generate_slang_explanation(
    term: str = Query(..., description="The slang term to explain"),
    context: Optional[str] = Query(None, description="Optional context for the term"),
    current_user: User = Depends(get_current_user)
):
    """Use AI to generate an explanation for a slang term"""
    explanation_json = await ai_service.generate_explanation(term, context)
    
    # Parse the JSON response if it's a string
    if isinstance(explanation_json, str):
        explanation = json.loads(explanation_json)
    else:
        explanation = explanation_json
    
    # Convert to SlangTermCreate schema
    result = SlangTermCreate(
        term=term,
        meaning=explanation.get("meaning", ""),
        origin=explanation.get("origin"),
        part_of_speech=explanation.get("part_of_speech"),
        pronunciation=explanation.get("pronunciation"),
        alternative_spellings=explanation.get("alternative_spellings", []),
        examples=explanation.get("examples", []),
        context=context
    )
    
    return result

@router.post("/translations", response_model=TranslationResponse)
async def create_translation(
    translation: TranslationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a translation for a slang term"""
    # Check if slang term exists
    slang_term = db.query(SlangTerm).filter(SlangTerm.id == translation.slang_id).first()
    if not slang_term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slang term with ID {translation.slang_id} not found"
        )
    
    # Check if translation already exists for this language
    existing = (
        db.query(SlangTranslation)
        .filter(
            SlangTranslation.slang_id == translation.slang_id,
            SlangTranslation.language == translation.language
        )
        .first()
    )
    
    if existing:
        # Update existing translation
        existing.translation = translation.translation
        existing.examples = translation.examples or []
        db.commit()
        db.refresh(existing)
        return TranslationResponse.from_orm(existing)
    
    # Create new translation
    new_translation = SlangTranslation(
        slang_id=translation.slang_id,
        language=translation.language,
        translation=translation.translation,
        examples=translation.examples or []
    )
    
    db.add(new_translation)
    db.commit()
    db.refresh(new_translation)
    
    return TranslationResponse.from_orm(new_translation)

@router.post("/generate-translation", response_model=Dict)
async def generate_translation(
    term: str = Query(..., description="The slang term to translate"),
    target_language: str = Query(..., description="The target language code"),
    meaning: Optional[str] = Query(None, description="Optional meaning of the slang term"),
    examples: Optional[str] = Query(None, description="Optional examples separated by |"),
    current_user: User = Depends(get_current_user)
):
    """Use AI to generate a translation for a slang term"""
    examples_list = examples.split("|") if examples else None
    
    translation_json = await ai_service.translate_slang(term, target_language, meaning, examples_list)
    
    # Parse the JSON response if it's a string
    if isinstance(translation_json, str):
        translation = json.loads(translation_json)
    else:
        translation = translation_json
    
    return translation