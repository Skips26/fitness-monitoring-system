"""
AI Coach routes — Gemini-powered fitness chatbot.

Proxies chat messages to Gemini 2.5 Flash with full user profile
and workout context injected as a system prompt. The API key stays
server-side so it is never exposed to the browser.

Uses direct REST API calls (requests) instead of the google-genai SDK
to avoid httpx version conflicts with Supabase.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import requests as http_requests
from auth import get_current_user
from database import get_supabase_admin
from config import GEMINI_API_KEY

router = APIRouter(prefix="/ai-coach", tags=["AI Coach"])

# Gemini API endpoint
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


# ── Schemas ──────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str          # "user" or "model"
    content: str


class ChatRequest(BaseModel):
    workout_id: str
    message: str
    history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    reply: str


# ── Workout type display names ───────────────────────────────────────────────

TYPE_LABELS = {
    "HILV": "High Intensity, Low Volume (HILV)",
    "LIHV": "Low Intensity, High Volume (LIHV)",
    "hypertrophy": "Hypertrophy (standard 8-12 rep bodybuilding)",
    "endurance_lifting": "Endurance Lifting (high rep endurance)",
}


# ── System Prompt Builder ────────────────────────────────────────────────────

def build_system_prompt(profile: dict, workout: dict) -> str:
    """
    Build a rich system prompt that gives Gemini full context about the user
    and their analyzed workout, so it can give personalized coaching.
    """
    workout_type = workout.get("workout_type", "unknown")
    type_label = TYPE_LABELS.get(workout_type, workout_type)

    # Format top factors if available
    top_factors_text = ""
    if workout.get("top_factors"):
        factors = workout["top_factors"]
        lines = []
        for f in factors[:5]:
            name = f.get("feature", f.get("name", "unknown"))
            impact = f.get("impact", f.get("shap_value", 0))
            direction = "↑ positive" if impact > 0 else "↓ negative"
            lines.append(f"  - {name}: {impact:+.3f} ({direction} impact)")
        top_factors_text = "\n".join(lines)

    return f"""You are an expert AI fitness coach integrated into a workout monitoring system.
You have deep knowledge of exercise science, training programming, recovery, nutrition,
and biomechanics. You are friendly, encouraging, and give specific, actionable advice.

═══════════════════════════════════════════════════════════════
USER PROFILE
═══════════════════════════════════════════════════════════════
- Name: {profile.get('first_name', 'User')} {profile.get('last_name', '')}
- Age: {profile.get('age', 'N/A')} years
- Weight: {profile.get('weight_kg', 'N/A')} kg
- Body Fat: {profile.get('body_fat_pct', 'N/A')}%
- Fitness Level: {profile.get('fitness_level', 'N/A')}
- Athlete Type: {profile.get('athlete_type', 'N/A')}
- Limb Length: {profile.get('limb_length', 'N/A')}

═══════════════════════════════════════════════════════════════
ANALYZED WORKOUT
═══════════════════════════════════════════════════════════════
- Training Style: {type_label}
- Duration: {workout.get('duration_mins', 'N/A')} minutes
- Average Heart Rate: {workout.get('avg_hr', 'N/A')} BPM
- Max Heart Rate: {workout.get('max_hr', 'N/A')} BPM
- Heart Rate Spikes: {workout.get('hr_spikes', 'N/A')}
- Time in Low HR Zone: {workout.get('pct_time_low', 'N/A')}%
- Average EMG (muscle activation): {workout.get('avg_emg', 'N/A')}
- EMG Fatigue Index: {workout.get('emg_fatigue', 'N/A')}%
- Total Reps: {workout.get('total_reps', 'N/A')}

AI EFFECTIVENESS RATING: {workout.get('effectiveness_name', 'N/A')}
Confidence: {round(workout.get('confidence', 0) * 100)}%
AI Explanation: {workout.get('explanation', 'N/A')}

Key Impact Factors:
{top_factors_text if top_factors_text else '  (not available)'}

═══════════════════════════════════════════════════════════════
INSTRUCTIONS
═══════════════════════════════════════════════════════════════
1. Answer any training-related question using the user's profile and workout data above.
2. Tailor your advice to their specific training style ({type_label}).
3. Reference their actual sensor data (heart rate, EMG, reps, etc.) when relevant.
4. Consider their fitness level, body composition, and athlete type in your recommendations.
5. If the workout effectiveness is Low or Moderate, suggest specific improvements.
6. Be concise but thorough. Use bullet points for actionable tips.
7. If asked about something unrelated to fitness/training, politely redirect to training topics.
8. Use the user's first name ({profile.get('first_name', 'User')}) occasionally to keep it personal.
"""


# ── Gemini API caller (direct REST) ─────────────────────────────────────────

def call_gemini(system_prompt: str, history: list, user_message: str) -> str:
    """
    Call the Gemini 2.5 Flash API directly via REST.
    Avoids the google-genai SDK to prevent httpx version conflicts.
    """
    # Build contents array with conversation history
    contents = []

    for msg in history:
        contents.append({
            "role": msg.role,
            "parts": [{"text": msg.content}],
        })

    # Add the current user message
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}],
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        },
    }

    response = http_requests.post(
        f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )

    if response.status_code != 200:
        error_detail = response.json().get("error", {}).get("message", response.text)
        raise Exception(f"Gemini API error ({response.status_code}): {error_detail}")

    data = response.json()

    # Extract text from response
    candidates = data.get("candidates", [])
    if not candidates:
        raise Exception("No response generated by Gemini.")

    parts = candidates[0].get("content", {}).get("parts", [])
    reply_text = "".join(p.get("text", "") for p in parts)

    return reply_text or "I'm sorry, I couldn't generate a response. Please try again."


# ── Chat Endpoint ────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_with_coach(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
):
    """
    Send a message to the AI Coach. The coach has full context about the
    user's profile and the specific analyzed workout.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Coach is not configured. Missing GEMINI_API_KEY.",
        )

    db = get_supabase_admin()

    # 1. Fetch the workout (must belong to this user and be analyzed)
    workout_result = (
        db.table("workouts")
        .select("*")
        .eq("id", body.workout_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not workout_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found.",
        )

    workout = workout_result.data[0]

    if workout.get("status") != "analyzed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI Coach is only available for analyzed workouts.",
        )

    # 2. Fetch user profile
    profile_result = (
        db.table("profiles")
        .select("*")
        .eq("id", user["id"])
        .execute()
    )

    if not profile_result.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile required for AI Coach.",
        )

    profile = profile_result.data[0]

    # 3. Build system prompt with full context
    system_prompt = build_system_prompt(profile, workout)

    # 4. Call Gemini API
    try:
        reply_text = call_gemini(system_prompt, body.history or [], body.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Coach error: {str(e)}",
        )

    return ChatResponse(reply=reply_text)
