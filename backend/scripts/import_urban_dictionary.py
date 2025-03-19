# scripts/import_urban_dictionary.py
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import SlangTerm
from ai_service import fetch_from_urban_dictionary

async def import_terms(terms):
    """Import terms from Urban Dictionary"""
    db = SessionLocal()
    
    for term in terms:
        # Check if term already exists
        existing = db.query(SlangTerm).filter(SlangTerm.term == term).first()
        if existing:
            print(f"Term '{term}' already exists, skipping...")
            continue
            
        print(f"Importing '{term}'...")
        definition = await fetch_from_urban_dictionary(term)
        
        new_term = SlangTerm(
            term=term,
            meaning=definition.get("meaning", ""),
            origin=definition.get("origin"),
            examples=definition.get("examples", []),
            context="Imported from Urban Dictionary",
            is_verified=True
        )
        
        db.add(new_term)
    
    db.commit()
    print("Import complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_urban_dictionary.py term1 term2 term3 ...")
        sys.exit(1)
        
    terms = sys.argv[1:]
    asyncio.run(import_terms(terms))