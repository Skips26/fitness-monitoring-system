"""
=============================================================================
  FITNESS MONITORING SYSTEM — FastAPI Backend
  ────────────────────────────────────────────
  REST API for the IoT Fitness Monitoring System.
  Handles user profiles, workout data from Raspberry Pi,
  and AI-powered workout effectiveness predictions.
=============================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS
from routers import profiles, workouts

# =============================================================================
#  APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="Fitness Monitoring System API",
    description="REST API for IoT workout tracking with AI-powered effectiveness analysis",
    version="1.0.0",
)

# CORS — allow the React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
#  ROUTERS
# =============================================================================

app.include_router(profiles.router)
app.include_router(workouts.router)


# =============================================================================
#  HEALTH CHECK
# =============================================================================

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "service": "Fitness Monitoring System API",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
