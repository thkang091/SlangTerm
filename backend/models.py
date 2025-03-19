from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime, Table, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base

# Association table for user favorites
user_favorites = Table(
    "user_favorites",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id")),
    Column("slang_id", Integer, ForeignKey("slang_terms.id")),
)

class SlangTerm(Base):
    __tablename__ = "slang_terms"
    
    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(100), nullable=False, index=True)
    meaning = Column(Text, nullable=False)
    origin = Column(String(255))
    context = Column(String(255))  # Where/how the slang is typically used
    part_of_speech = Column(String(50))
    pronunciation = Column(String(255))
    alternative_spellings = Column(JSON)  # Store as JSON array
    examples = Column(JSON)  # Store as JSON array of example sentences
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_verified = Column(Boolean, default=False)
    submitted_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Vector embedding for the term (cached)
    embedding = Column(JSON)
    
    # Relationships
    votes = relationship("SlangVote", back_populates="slang_term")
    translations = relationship("SlangTranslation", back_populates="slang_term")
    submitter = relationship("User", back_populates="submitted_terms")
    favorited_by = relationship("User", secondary=user_favorites, back_populates="favorites")

class SlangTranslation(Base):
    __tablename__ = "slang_translations"
    
    id = Column(Integer, primary_key=True, index=True)
    slang_id = Column(Integer, ForeignKey("slang_terms.id"))
    language = Column(String(10), nullable=False)  # Language code (e.g., "es", "fr")
    translation = Column(Text, nullable=False)
    examples = Column(JSON)  # Store as JSON array of translated examples
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    slang_term = relationship("SlangTerm", back_populates="translations")

class SlangVote(Base):
    __tablename__ = "slang_votes"
    
    id = Column(Integer, primary_key=True, index=True)
    slang_id = Column(Integer, ForeignKey("slang_terms.id"))
    user_id = Column(String, ForeignKey("users.id"))
    vote = Column(Integer)  # 1 for upvote, -1 for downvote
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    slang_term = relationship("SlangTerm", back_populates="votes")
    user = relationship("User", back_populates="votes")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)  # Firebase UID
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=True)
    native_language = Column(String(10), nullable=True)
    learning_languages = Column(JSON)  # JSON array of language codes
    role = Column(String(20), default="user")  # "user", "moderator", "admin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    favorites = relationship("SlangTerm", secondary=user_favorites, back_populates="favorited_by")
    search_history = relationship("SearchHistory", back_populates="user")
    submitted_terms = relationship("SlangTerm", back_populates="submitter")
    votes = relationship("SlangVote", back_populates="user")

class SearchHistory(Base):
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    query = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="search_history")