import numpy as np
import faiss
import json
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from models import SlangTerm
from config import EMBEDDINGS_MODEL, EMBEDDINGS_DIMENSION, SIMILARITY_THRESHOLD

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDINGS_MODEL)
        self.dimension = EMBEDDINGS_DIMENSION
        self.threshold = SIMILARITY_THRESHOLD
        self.index = None
        self.slang_ids = []
    
    def get_embedding(self, text):
        """Generate embeddings for a text string"""
        return self.model.encode(text).tolist()
    
    def build_index(self, db: Session):
        """Build FAISS index from all verified slang terms in the database"""
        slang_terms = db.query(SlangTerm).filter(SlangTerm.is_verified == True).all()
        
        if not slang_terms:
            # Create empty index if no terms exist
            self.index = faiss.IndexFlatL2(self.dimension)
            self.slang_ids = []
            return
        
        # Get embeddings either from the database or generate new ones
        embeddings = []
        self.slang_ids = []
        
        for term in slang_terms:
            if term.embedding:
                # Use cached embedding
                embedding = np.array(term.embedding, dtype=np.float32)
            else:
                # Generate new embedding
                text_to_embed = f"{term.term} {term.meaning}"
                if term.examples and isinstance(term.examples, list) and len(term.examples) > 0:
                    text_to_embed += " " + " ".join(term.examples[:2])  # Add first two examples
                
                embedding = self.model.encode(text_to_embed)
                
                # Cache the embedding in the database
                term.embedding = embedding.tolist()
                db.commit()
            
            embeddings.append(embedding)
            self.slang_ids.append(term.id)
        
        # Convert to numpy array and build FAISS index
        embeddings_np = np.array(embeddings, dtype=np.float32)
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings_np)
    
    def search(self, query, limit=10):
        """Search for similar slang terms using vector similarity"""
        if not self.index or self.index.ntotal == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode(query)
        query_embedding = np.array([query_embedding], dtype=np.float32)
        
        # Search the index
        distances, indices = self.index.search(query_embedding, limit)
        
        # Convert to slang IDs with similarity scores
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.slang_ids):  # Valid index
                similarity = 1.0 - (distances[0][i] / 2.0)  # Convert L2 distance to similarity
                if similarity >= self.threshold:
                    results.append({
                        "slang_id": self.slang_ids[idx],
                        "similarity": float(similarity)
                    })
        
        return results
    
    def find_similar_terms(self, term_text, db: Session, limit=5):
        """Find similar terms to a given text"""
        if not self.index or self.index.ntotal == 0:
            return []
        
        # Generate embedding for the term
        query_embedding = self.model.encode(term_text)
        query_embedding = np.array([query_embedding], dtype=np.float32)
        
        # Search the index
        distances, indices = self.index.search(query_embedding, limit + 1)  # +1 to account for possibly finding self
        
        # Get similar terms
        similar_terms = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.slang_ids):
                slang_id = self.slang_ids[idx]
                
                # Fetch term from database
                term = db.query(SlangTerm).filter(SlangTerm.id == slang_id).first()
                
                if term and term.term.lower() != term_text.lower():  # Skip self
                    similarity = 1.0 - (distances[0][i] / 2.0)
                    if similarity >= self.threshold:
                        similar_terms.append({
                            "id": term.id,
                            "term": term.term,
                            "similarity": float(similarity)
                        })
                        
                        if len(similar_terms) >= limit:
                            break
        
        return similar_terms
    
    def batch_index_update(self, db: Session, term_ids=None):
        """Update embeddings for specific terms or rebuild entire index"""
        if term_ids:
            # Update specific terms
            terms = db.query(SlangTerm).filter(
                SlangTerm.id.in_(term_ids),
                SlangTerm.is_verified == True
            ).all()
            
            for term in terms:
                text_to_embed = f"{term.term} {term.meaning}"
                if term.examples and isinstance(term.examples, list) and len(term.examples) > 0:
                    text_to_embed += " " + " ".join(term.examples[:2])
                
                embedding = self.model.encode(text_to_embed)
                term.embedding = embedding.tolist()
            
            db.commit()
        
        # Rebuild full index
        self.build_index(db)

# Create a singleton instance
embedding_service = EmbeddingService()