import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://slang_user:slang_password@localhost:5432/slang_dictionary")# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4")

# Vector embeddings settings
EMBEDDINGS_MODEL = "all-MiniLM-L6-v2"  # Use a standard model that's well-supported
EMBEDDINGS_DIMENSION = int(os.getenv("EMBEDDINGS_DIMENSION", "384"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

# Firebase settings
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "firebase-credentials.json")

# App settings
ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:19000", "http://localhost:19006", "exp://YOUR_IP:19000"]
MAX_SUBMISSIONS_PER_DAY = int(os.getenv("MAX_SUBMISSIONS_PER_DAY", "5"))