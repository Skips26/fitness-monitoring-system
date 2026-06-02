"""
Workout routes — receive sensor data, manage workouts, trigger analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from auth import get_current_user
from database import get_supabase_admin
from ml.predictor import predict_workout

router = APIRouter(prefix="/workouts", tags=["Workouts"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class WorkoutSensorData(BaseModel):
    """Data sent by the Raspberry Pi after a workout session."""
    user_id: str  # Which user this workout belongs to
    duration_mins: float = Field(ge=0.1)
    avg_hr: float = Field(ge=0)
    max_hr: float = Field(ge=0)
    hr_spikes: int = Field(ge=0)
    pct_time_low: float = Field(ge=0, le=100)
    avg_emg: float = Field(ge=0, le=1000)
    emg_fatigue: float = Field(ge=0, le=60)
    total_reps: int = Field(ge=0)


class WorkoutTypeUpdate(BaseModel):
    """User selects the workout type after data arrives."""
    workout_type: Literal["HILV", "LIHV", "hypertrophy", "endurance_lifting"]


class WorkoutRepsUpdate(BaseModel):
    """User manually enters the rep count for a workout."""
    total_reps: int = Field(ge=0)


class WorkoutResponse(BaseModel):
    id: str
    user_id: str
    workout_type: Optional[str] = None
    duration_mins: float
    avg_hr: float
    max_hr: float
    hr_spikes: int
    pct_time_low: float
    avg_emg: float
    emg_fatigue: float
    total_reps: int
    effectiveness_label: Optional[int] = None
    effectiveness_name: Optional[str] = None
    confidence: Optional[float] = None
    probabilities: Optional[dict] = None
    explanation: Optional[str] = None
    top_factors: Optional[list] = None
    status: str
    recorded_at: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
async def receive_workout(sensor_data: WorkoutSensorData):
    """
    Receive workout sensor data from the Raspberry Pi.
    No authentication required — the Pi sends data with the user_id.
    Workout is saved as 'pending' until the user selects a workout_type.
    """
    db = get_supabase_admin()

    # Verify the user exists
    user = db.table("profiles").select("id").eq("id", sensor_data.user_id).execute()
    if not user.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {sensor_data.user_id} not found.",
        )

    data = {
        "user_id": sensor_data.user_id,
        "duration_mins": sensor_data.duration_mins,
        "avg_hr": sensor_data.avg_hr,
        "max_hr": sensor_data.max_hr,
        "hr_spikes": sensor_data.hr_spikes,
        "pct_time_low": sensor_data.pct_time_low,
        "avg_emg": sensor_data.avg_emg,
        "emg_fatigue": sensor_data.emg_fatigue,
        "total_reps": sensor_data.total_reps,
        "status": "pending",
    }

    result = db.table("workouts").insert(data).execute()
    return result.data[0]


@router.get("", response_model=List[WorkoutResponse])
async def list_workouts(user: dict = Depends(get_current_user)):
    """List all workouts for the current user, newest first."""
    db = get_supabase_admin()

    result = (
        db.table("workouts")
        .select("*")
        .eq("user_id", user["id"])
        .order("recorded_at", desc=True)
        .execute()
    )

    return result.data


@router.get("/{workout_id}", response_model=WorkoutResponse)
async def get_workout(workout_id: str, user: dict = Depends(get_current_user)):
    """Get a single workout's details including AI prediction results."""
    db = get_supabase_admin()

    result = (
        db.table("workouts")
        .select("*")
        .eq("id", workout_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found.",
        )

    return result.data[0]


@router.put("/{workout_id}/type", response_model=WorkoutResponse)
async def set_workout_type(
    workout_id: str,
    body: WorkoutTypeUpdate,
    user: dict = Depends(get_current_user),
):
    """Set the workout type for a pending workout."""
    db = get_supabase_admin()

    result = (
        db.table("workouts")
        .update({"workout_type": body.workout_type})
        .eq("id", workout_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found.",
        )

    return result.data[0]


@router.put("/{workout_id}/reps", response_model=WorkoutResponse)
async def update_workout_reps(
    workout_id: str,
    body: WorkoutRepsUpdate,
    user: dict = Depends(get_current_user),
):
    """Manually set the rep count for a workout (used when MPU sensor is not active)."""
    db = get_supabase_admin()

    result = (
        db.table("workouts")
        .update({"total_reps": body.total_reps})
        .eq("id", workout_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found.",
        )

    return result.data[0]


@router.post("/{workout_id}/analyze", response_model=WorkoutResponse)
async def analyze_workout(
    workout_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Run AI prediction on a workout.
    Requires:
      1. The workout must have a workout_type set
      2. The user must have a complete profile (demographics)

    Merges 6 demographic features + workout_type + 8 sensor features → XGBoost prediction.
    """
    db = get_supabase_admin()

    # 1. Fetch the workout
    workout_result = (
        db.table("workouts")
        .select("*")
        .eq("id", workout_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not workout_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found.",
        )

    workout = workout_result.data[0]

    if not workout.get("workout_type"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workout type must be set before analysis. Use PUT /workouts/{id}/type first.",
        )

    # 2. Fetch user demographics
    profile_result = (
        db.table("profiles")
        .select("age, weight_kg, fitness_level, athlete_type, body_fat_pct, limb_length")
        .eq("id", user["id"])
        .execute()
    )

    if not profile_result.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile with demographics required for analysis.",
        )

    profile = profile_result.data[0]

    # 3. Merge features and run prediction
    features = {
        # Demographics (6 + weight)
        "age": profile["age"],
        "weight_kg": float(profile["weight_kg"]),
        "fitness_level": profile["fitness_level"],
        "workout_type": workout["workout_type"],
        "athlete_type": profile["athlete_type"],
        "body_fat_pct": float(profile["body_fat_pct"]),
        "limb_length": profile["limb_length"],
        # Sensor data (8)
        "duration_mins": float(workout["duration_mins"]),
        "avg_hr": float(workout["avg_hr"]),
        "max_hr": float(workout["max_hr"]),
        "hr_spikes": workout["hr_spikes"],
        "pct_time_low": float(workout["pct_time_low"]),
        "avg_emg": float(workout["avg_emg"]),
        "emg_fatigue": float(workout["emg_fatigue"]),
        "total_reps": workout["total_reps"],
    }

    prediction = predict_workout(features)

    # 4. Save prediction results
    update_data = {
        "effectiveness_label": prediction["label"],
        "effectiveness_name": prediction["label_name"],
        "confidence": prediction["confidence"],
        "probabilities": prediction["probabilities"],
        "explanation": prediction["explanation"],
        "top_factors": prediction["top_factors"],
        "status": "analyzed",
    }

    updated = (
        db.table("workouts")
        .update(update_data)
        .eq("id", workout_id)
        .execute()
    )

    return updated.data[0]
