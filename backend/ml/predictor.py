"""
ML Predictor — loads the trained XGBoost model and generates predictions
with SHAP explanations.

Loads the model once at import time and reuses it for all predictions.
"""

import json
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
import shap

from config import MODEL_PATH, MODEL_CONFIG_PATH

# =============================================================================
#  MODEL LOADING (singleton — loaded once at startup)
# =============================================================================

print(f"[ML] Loading model from: {MODEL_PATH}")
model = joblib.load(MODEL_PATH)
print(f"[ML] Model loaded successfully")

with open(MODEL_CONFIG_PATH, "r") as f:
    model_config = json.load(f)

FEATURE_COLS = model_config["feature_columns"]
LABEL_NAMES = {int(k): v for k, v in model_config["label_names"].items()}
FEATURE_DESCRIPTIONS = model_config["feature_descriptions"]

# Create SHAP explainer
print("[ML] Initializing SHAP explainer...")
try:
    explainer = shap.TreeExplainer(model)
except ValueError:
    # Workaround for XGBoost > 2.0 multi-class format
    import shap.explainers._tree
    import ast

    original_decode = shap.explainers._tree.decode_ubjson_buffer

    def patched_decode(*args, **kwargs):
        jmodel = original_decode(*args, **kwargs)
        base_score = (
            jmodel.get("learner", {})
            .get("learner_model_param", {})
            .get("base_score", "")
        )
        if isinstance(base_score, str) and base_score.startswith("["):
            scores = ast.literal_eval(base_score.replace("E", "e"))
            jmodel["learner"]["learner_model_param"]["base_score"] = str(scores[0])
        return jmodel

    shap.explainers._tree.decode_ubjson_buffer = patched_decode
    explainer = shap.TreeExplainer(model)

print("[ML] SHAP explainer ready")


# =============================================================================
#  THRESHOLDS FOR DESCRIPTIONS
# =============================================================================

CATEGORICAL_COLS = ['fitness_level', 'workout_type', 'athlete_type', 'limb_length']

_THRESHOLDS = {
    'age':           (None,  'age',                        'age'),
    'weight_kg':     (80,    'heavier body weight',        'lighter body weight'),
    'body_fat_pct':  (20,    'higher body fat',            'lower body fat'),
    'duration_mins': (40,    'long session duration',      'short session duration'),
    'avg_hr':        (125,   'elevated avg heart rate',    'low avg heart rate'),
    'max_hr':        (145,   'high peak heart rate',       'low peak heart rate'),
    'hr_spikes':     (4,     'frequent HR spikes',         'few HR spikes'),
    'pct_time_low':  (25,    'lots of low-HR zone time',   'minimal low-HR zone time'),
    'avg_emg':       (400,   'strong muscle engagement',   'weak muscle engagement'),
    'emg_fatigue':   (18,    'significant muscle fatigue', 'minimal muscle fatigue'),
    'total_reps':    (90,    'high rep count',             'low rep count'),
}

def _format_value(feat, val):
    if feat in ['avg_hr', 'max_hr']:
        return f"{val:.0f} BPM"
    elif feat in ['pct_time_low', 'emg_fatigue', 'body_fat_pct']:
        return f"{val:.1f}%"
    elif feat == 'avg_emg':
        return f"{val:.0f} (EMG units)"
    elif feat == 'duration_mins':
        return f"{val:.0f} min"
    elif feat == 'weight_kg':
        return f"{val:.1f} kg"
    elif feat == 'age':
        return f"{int(val)} yrs"
    else:
        return f"{val}"

# =============================================================================
#  PREDICTION FUNCTION
# =============================================================================

def predict_workout(features: dict, top_k: int = 3) -> dict:
    """
    Predict workout effectiveness and generate a human-readable SHAP explanation.

    Parameters:
        features: dict with all 14 features (6 demographic + 8 sensor)
        top_k:    number of top SHAP factors to include in explanation

    Returns:
        dict with label, label_name, confidence, probabilities,
        explanation, and top_factors
    """
    # Build DataFrame with correct column order
    sample_df = pd.DataFrame([features], columns=FEATURE_COLS)

    # Convert categoricals
    categorical_cols = ["fitness_level", "workout_type", "athlete_type", "limb_length"]
    for col in categorical_cols:
        sample_df[col] = sample_df[col].astype("category")

    # Predict
    pred_label = int(model.predict(sample_df)[0])
    pred_proba = model.predict_proba(sample_df)[0]
    confidence = float(pred_proba[pred_label])

    # SHAP values for the predicted class
    shap_vals = explainer.shap_values(sample_df)

    if isinstance(shap_vals, list):
        shap_for_class = shap_vals[pred_label][0]
    elif isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) == 3:
        if shap_vals.shape[2] == 4:
            shap_for_class = shap_vals[0, :, pred_label]
        else:
            shap_for_class = shap_vals[0, pred_label, :]
    else:
        try:
            vals = shap_vals.values if hasattr(shap_vals, "values") else shap_vals
            if len(vals.shape) == 3:
                if vals.shape[2] == 4:
                    shap_for_class = vals[0, :, pred_label]
                else:
                    shap_for_class = vals[0, pred_label, :]
            else:
                shap_for_class = vals[0]
        except Exception:
            shap_for_class = np.zeros(len(FEATURE_COLS))

    # Rank features by positive SHAP contribution to the predicted class
    feat_shap = list(zip(FEATURE_COLS, shap_for_class, sample_df.iloc[0]))
    feat_shap.sort(key=lambda x: x[1], reverse=True)

    # Build explanation
    top_factors = []
    for feat_name, shap_val, feat_val in feat_shap[:top_k]:
        direction = "positive" if shap_val > 0 else "negative"
        
        if feat_name in CATEGORICAL_COLS:
            desc = f"{feat_name.replace('_', ' ')} ({feat_val})"
        elif feat_name in _THRESHOLDS and _THRESHOLDS[feat_name][0] is not None:
            thresh, high_label, low_label = _THRESHOLDS[feat_name]
            label_txt = high_label if float(feat_val) > thresh else low_label
            desc = f"{label_txt} ({_format_value(feat_name, float(feat_val))})"
        else:
            desc = f"{feat_name.replace('_', ' ')} ({_format_value(feat_name, float(feat_val))})"

        top_factors.append(
            {
                "feature": feat_name,
                "value": _serialize_value(feat_val),
                "shap_value": round(float(shap_val), 4),
                "description": desc,
                "direction": direction,
            }
        )

    # Compose natural language explanation
    reasons = [f["description"] for f in top_factors]
    explanation = (
        f"{LABEL_NAMES[pred_label]} effectiveness "
        f"(confidence: {confidence:.0%}). "
        f"Key factors: {'; '.join(reasons)}."
    )

    return {
        "label": pred_label,
        "label_name": LABEL_NAMES[pred_label],
        "confidence": round(confidence, 4),
        "probabilities": {
            LABEL_NAMES[i]: round(float(pred_proba[i]), 4) for i in range(4)
        },
        "explanation": explanation,
        "top_factors": top_factors,
    }


def _serialize_value(val):
    """Convert numpy/pandas types to JSON-serializable Python types."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    if isinstance(val, (np.ndarray,)):
        return val.tolist()
    return val
