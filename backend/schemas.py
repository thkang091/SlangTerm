from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

# Slang Term Schemas
class SlangTermBase(BaseModel):
    term: str
    meaning: str
    origin: Optional[str] = None
    context: Optional[str] = None
    part_of_speech: Optional[str] = None
    pronunciation: Optional[str] = None
    alternative_spellings: Optional[List[str]] = None
    examples: Optional[List[str]] = None

class SlangTermCreate(SlangTermBase):
    pass

class SlangTermResponse(SlangTermBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_verified: bool
    vote_count: int = 0
    
    class Config:
        orm_mode = True

class SlangTermDetail(SlangTermResponse):
    translations: Optional[List['TranslationResponse']] = None
    submitter: Optional['UserBasicInfo'] = None
    
    class Config:
        orm_mode = True

# Translation Schemas
class TranslationBase(BaseModel):
    language: str
    translation: str
    examples: Optional[List[str]] = None

class TranslationCreate(TranslationBase):
    slang_id: int

class TranslationResponse(TranslationBase):
    id: int
    slang_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# Vote Schemas
class VoteCreate(BaseModel):
    slang_id: int
    vote: int = Field(..., ge=-1, le=1)  # -1, 0, or 1

class VoteResponse(BaseModel):
    id: int
    slang_id: int
    vote: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    native_language: Optional[str] = None
    learning_languages: Optional[List[str]] = None

class UserCreate(UserBase):
    id: str  # Firebase UID

class UserResponse(UserBase):
    id: str
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class UserBasicInfo(BaseModel):
    id: str
    username: Optional[str] = None
    
    class Config:
        orm_mode = True

# Search Schemas
class SearchQuery(BaseModel):
    query: str
    semantic: bool = True
    limit: int = 10

class SearchResponse(BaseModel):
    results: List[SlangTermResponse]
    query: str
    count: int
    
    class Config:
        orm_mode = True

# AI Generation Schemas
class ExplanationRequest(BaseModel):
    term: str
    context: Optional[str] = None

class ExplanationResponse(BaseModel):
    term: str
    meaning: str
    examples: List[str]
    additional_info: Optional[Dict[str, Any]] = None

class TranslationRequest(BaseModel):
    term: str
    target_language: str
    meaning: Optional[str] = None
    examples: Optional[List[str]] = None

# Admin Schemas
class ModerateRequest(BaseModel):
    slang_id: int
    action: str  # "approve", "reject", "update"
    updates: Optional[SlangTermBase] = None
    reason: Optional[str] = None

class StatsResponse(BaseModel):
    total_terms: int
    verified_terms: int
    pending_terms: int
    recent_submissions: List[SlangTermResponse]
    popular_terms: List[SlangTermResponse]

# Favorite Schemas
class FavoriteToggle(BaseModel):
    slang_id: int