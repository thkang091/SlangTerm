from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, engine, Base
from config import ALLOWED_ORIGINS
from routers import slang, search, users, admin, community
from embeddings import embedding_service

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize app
app = FastAPI(
    title="AI-Powered Slang Dictionary API",
    description="API for the ML-powered slang dictionary application",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(slang.router)
app.include_router(search.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(community.router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        db = next(get_db())
        # Build search index on startup
        if embedding_service.model:  # Only build if model loaded successfully
            embedding_service.build_index(db)
    except Exception as e:
        print(f"Error during startup: {str(e)}")

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to the Slang Dictionary API",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)