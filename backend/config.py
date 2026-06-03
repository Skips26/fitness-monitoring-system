"""
Application configuration — loads settings from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# Model path (relative to project root)
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "AI")
MODEL_PATH = os.path.join(MODEL_DIR, "workout_model.joblib")
MODEL_CONFIG_PATH = os.path.join(MODEL_DIR, "model_config.json")

# Gemini AI Coach
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

