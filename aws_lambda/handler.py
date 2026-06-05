"""
=============================================================================
  AWS Lambda — Workout Data Relay
  ────────────────────────────────
  Receives workout sensor data from the Raspberry Pi via API Gateway,
  and forwards it to the FastAPI backend (which saves it to Supabase).

  After forwarding, AWS is no longer needed — the website takes over.
=============================================================================

Environment Variables (set in Lambda console):
    BACKEND_URL  —  e.g. "https://your-backend.com" or "http://your-server-ip:8000"
"""

import json
import os
import urllib.request
import urllib.error


BACKEND_URL = os.environ.get("BACKEND_URL", "https://fitness-monitoring-system.onrender.com")


def lambda_handler(event, context):
    """
    API Gateway → Lambda handler.
    Expects a JSON body with workout sensor data + user_id.
    Forwards it to POST {BACKEND_URL}/workouts.
    """
    # ── Parse incoming body ──────────────────────────────────────────────
    try:
        if isinstance(event.get("body"), str):
            payload = json.loads(event["body"])
        else:
            payload = event.get("body") or event
    except (json.JSONDecodeError, TypeError) as e:
        return _response(400, {"error": f"Invalid JSON body: {e}"})

    # ── Validate required fields ─────────────────────────────────────────
    required = [
        "user_id", "duration_mins", "avg_hr", "max_hr",
        "hr_spikes", "pct_time_low", "avg_emg", "emg_fatigue", "total_reps",
    ]
    missing = [f for f in required if f not in payload]
    if missing:
        return _response(400, {"error": f"Missing fields: {missing}"})

    # ── Forward to FastAPI backend ───────────────────────────────────────
    backend_endpoint = f"{BACKEND_URL}/workouts"
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        backend_endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            response_body = json.loads(resp.read().decode("utf-8"))
            return _response(resp.status, {
                "message": "Workout data forwarded to backend successfully",
                "workout": response_body,
            })
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        return _response(e.code, {
            "error": f"Backend returned HTTP {e.code}",
            "detail": error_body[:500],
        })
    except urllib.error.URLError as e:
        return _response(502, {
            "error": f"Could not reach backend at {backend_endpoint}",
            "detail": str(e.reason),
        })
    except Exception as e:
        return _response(500, {"error": f"Unexpected error: {e}"})


def _response(status_code: int, body: dict) -> dict:
    """Format a proper API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
