import sys

print("Python version:", sys.version)

print("Step 1: Importing numpy")
import numpy as np
print("Step 2: Importing FAISS")
import faiss
print("Step 3: Importing SentenceTransformer")
from sentence_transformers import SentenceTransformer

print("Step 4: Loading model")
try:
    # Try with a small model first
    model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
    print("Model loaded successfully")
    
    # Test encoding
    print("Step 5: Testing encoding")
    test_embedding = model.encode("Test sentence")
    print("Encoding successful, shape:", test_embedding.shape)
    
    # Test FAISS
    print("Step 6: Testing FAISS")
    dimension = len(test_embedding)
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array([test_embedding], dtype=np.float32))
    print("FAISS index created and populated successfully")
    
except Exception as e:
    print(f"Error during testing: {type(e).__name__}: {str(e)}")