"""
Profile routes — manage user demographic data.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Literal
from auth import get_current_user
from database import get_supabase_admin

router = APIRouter(prefix="/profiles", tags=["Profiles"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=13, le=100)
    weight_kg: Optional[float] = Field(None, ge=50.0, le=130.0)
    fitness_level: Optional[Literal["low", "medium", "high"]] = None
    athlete_type: Optional[Literal["powerlifter", "hybrid", "gym_bro", "non_athletic"]] = None
    body_fat_pct: Optional[float] = Field(None, ge=3.0, le=50.0)
    limb_length: Optional[Literal["short", "medium", "long"]] = None


class ProfileCreate(BaseModel):
    first_name: str
    last_name: str
    age: int = Field(ge=13, le=100)
    weight_kg: float = Field(ge=50.0, le=130.0)
    fitness_level: Literal["low", "medium", "high"]
    athlete_type: Literal["powerlifter", "hybrid", "gym_bro", "non_athletic"]
    body_fat_pct: float = Field(ge=3.0, le=50.0)
    limb_length: Literal["short", "medium", "long"]


class ProfileResponse(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    fitness_level: Optional[str] = None
    athlete_type: Optional[str] = None
    body_fat_pct: Optional[float] = None
    limb_length: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(user: dict = Depends(get_current_user)):
    """Get the current user's profile and demographic data."""
    db = get_supabase_admin()
    result = db.table("profiles").select("*").eq("id", user["id"]).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create one first.",
        )

    return result.data[0]


@router.post("/me", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    profile: ProfileCreate,
    user: dict = Depends(get_current_user),
):
    """Create the current user's profile with demographic data."""
    db = get_supabase_admin()

    # Check if profile already exists
    existing = db.table("profiles").select("id").eq("id", user["id"]).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists. Use PUT to update.",
        )

    data = {
        "id": user["id"],
        **profile.model_dump(),
    }

    result = db.table("profiles").insert(data).execute()
    return result.data[0]


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    profile: ProfileUpdate,
    user: dict = Depends(get_current_user),
):
    """Update the current user's demographic data."""
    db = get_supabase_admin()

    # Only include non-None fields
    update_data = {k: v for k, v in profile.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    update_data["updated_at"] = "now()"

    result = (
        db.table("profiles")
        .update(update_data)
        .eq("id", user["id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )

    return result.data[0]
