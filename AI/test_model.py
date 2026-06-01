#!/usr/bin/env python3
"""
=============================================================================
  WORKOUT EFFECTIVENESS -- Interactive Manual Tester
  --------------------------------------------------
  Load the trained XGBoost model and test it with your own values.
  Press Enter to accept the default for any field.

  Run:  python test_model.py
=============================================================================
"""

import os
import json
import ast
import pandas as pd
import xgboost as xgb
import shap

# ---------------------------------------------------------------------------
#  0. PATHS
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
#  1. LOAD CONFIG + MODEL
# ---------------------------------------------------------------------------
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'model_config.json')
MODEL_PATH  = os.path.join(SCRIPT_DIR, 'workout_model.json')

try:
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("\n  [ERROR] model_config.json not found.")
    print("  Run train_model.py first to generate the model.\n")
    exit(1)

FEATURE_COLS = config['feature_columns']
LABEL_NAMES  = {int(k): v for k, v in config['label_names'].items()}
LABEL_TAG    = {0: '[LOW]     ', 1: '[MODERATE]', 2: '[HIGH]    ', 3: '[MAXIMUM] '}

model = xgb.XGBClassifier(enable_categorical=True)
model.load_model(MODEL_PATH)

# ---------------------------------------------------------------------------
#  2. SHAP EXPLAINER  (with XGBoost 2.x patch)
# ---------------------------------------------------------------------------
try:
    import shap.explainers._tree
    original_decode = shap.explainers._tree.decode_ubjson_buffer

    def patched_decode(*args, **kwargs):
        jmodel = original_decode(*args, **kwargs)
        base_score = jmodel.get("learner", {}).get(
            "learner_model_param", {}).get("base_score", "")
        if isinstance(base_score, str) and base_score.startswith('['):
            scores = ast.literal_eval(base_score.replace('E', 'e'))
            jmodel["learner"]["learner_model_param"]["base_score"] = str(scores[0])
        return jmodel

    shap.explainers._tree.decode_ubjson_buffer = patched_decode
except AttributeError:
    pass  # newer SHAP version -- no patch needed

explainer = shap.TreeExplainer(model)

# ---------------------------------------------------------------------------
#  3. PREDICTION + EXPLANATION
# ---------------------------------------------------------------------------
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


def predict_and_explain(workout: dict, top_k: int = 4):
    """Predict workout effectiveness label + SHAP explanation."""
    sample_df = pd.DataFrame([workout], columns=FEATURE_COLS)
    for col in CATEGORICAL_COLS:
        if col in sample_df.columns:
            sample_df[col] = sample_df[col].astype('category')

    pred_label = int(model.predict(sample_df)[0])
    pred_proba = model.predict_proba(sample_df)[0]
    confidence = float(pred_proba[pred_label])

    shap_vals = explainer.shap_values(sample_df)
    if isinstance(shap_vals, list):
        shap_for_class = shap_vals[pred_label][0]
    else:
        arr = shap_vals.values if hasattr(shap_vals, 'values') else shap_vals
        if arr.ndim == 3:
            shap_for_class = arr[0, :, pred_label] if arr.shape[2] == 4 else arr[0, pred_label, :]
        else:
            shap_for_class = arr[0]

    feat_shap = list(zip(FEATURE_COLS, shap_for_class, sample_df.iloc[0]))
    feat_shap.sort(key=lambda x: abs(x[1]), reverse=True)

    top_factors = []
    for feat_name, shap_val, feat_val in feat_shap[:top_k]:
        direction = '+' if shap_val > 0 else '-'
        if feat_name in CATEGORICAL_COLS:
            desc = f"{feat_name.replace('_', ' ')}: {feat_val}"
        elif feat_name in _THRESHOLDS and _THRESHOLDS[feat_name][0] is not None:
            thresh, high_label, low_label = _THRESHOLDS[feat_name]
            label_txt = high_label if feat_val > thresh else low_label
            desc = f"{label_txt} -> {_format_value(feat_name, feat_val)}"
        else:
            desc = f"{feat_name} -> {_format_value(feat_name, feat_val)}"

        top_factors.append({
            'feature': feat_name,
            'value': feat_val,
            'shap': float(shap_val),
            'direction': direction,
            'description': desc,
        })

    return {
        'label': pred_label,
        'label_name': LABEL_NAMES[pred_label],
        'confidence': confidence,
        'probabilities': {LABEL_NAMES[i]: round(float(pred_proba[i]), 4) for i in range(4)},
        'top_factors': top_factors,
    }


# ---------------------------------------------------------------------------
#  4. DISPLAY HELPER
# ---------------------------------------------------------------------------
BAR_WIDTH = 28


def _prob_bar(prob: float) -> str:
    filled = int(round(prob * BAR_WIDTH))
    return '#' * filled + '.' * (BAR_WIDTH - filled)


def print_result(result: dict):
    label   = result['label']
    name    = result['label_name']
    conf    = result['confidence']
    probs   = result['probabilities']
    factors = result['top_factors']

    print()
    print("=" * 60)
    print(f"  RESULT:  {name.upper()}  effectiveness")
    print(f"  Confidence: {conf:.1%}")
    print("=" * 60)

    print("\n  PROBABILITY BREAKDOWN")
    print("  " + "-" * 54)
    for i in range(4):
        lname = LABEL_NAMES[i]
        p = probs[lname]
        bar = _prob_bar(p)
        marker = " <-- PREDICTED" if i == label else ""
        print(f"  {LABEL_TAG[i]}  [{bar}]  {p:5.1%}{marker}")

    print("\n  TOP FACTORS  (SHAP-ranked, most influential first)")
    print("  " + "-" * 54)
    for i, f in enumerate(factors, 1):
        arrow = "^ UP  " if f['direction'] == '+' else "v DOWN"
        print(f"  {i}. [{arrow}]  {f['description']}")
        print(f"        SHAP: {f['shap']:+.4f}  |  feature: {f['feature']}")

    print()
    print("=" * 60)


# ---------------------------------------------------------------------------
#  5. INTERACTIVE INPUT HELPERS
# ---------------------------------------------------------------------------

def _ask(prompt: str, default, cast=float, valid=None):
    """Prompt user for a value. Returns default if Enter pressed."""
    while True:
        raw = input(f"  {prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = cast(raw)
            if valid and val not in valid:
                print(f"    ! Must be one of: {', '.join(valid)}")
                continue
            return val
        except (ValueError, TypeError):
            print(f"    ! Invalid input, expected {cast.__name__}.")


def collect_workout():
    """Prompt the user for all 15 workout features."""
    print()
    print("-" * 60)
    print("  PROFILE  (who you are)")
    print("-" * 60)
    age          = _ask("Age (years)",                         25,          int)
    weight_kg    = _ask("Body weight kg (50-130)",             80.0,        float)
    fitness_lvl  = _ask("Fitness level (low/medium/high)",     "medium",    str,
                         valid=['low', 'medium', 'high'])
    workout_type = _ask("Workout type (HILV/LIHV/hypertrophy/endurance_lifting)",
                         "hypertrophy", str,
                         valid=['HILV', 'LIHV', 'hypertrophy', 'endurance_lifting'])
    athlete_type = _ask("Athlete type (powerlifter/hybrid/gym_bro/non_athletic)",
                         "gym_bro", str,
                         valid=['powerlifter', 'hybrid', 'gym_bro', 'non_athletic'])
    body_fat_pct = _ask("Body fat % (5-35)",                  15.0,        float)
    limb_length  = _ask("Limb length (short/medium/long)",    "medium",    str,
                         valid=['short', 'medium', 'long'])

    print()
    print("-" * 60)
    print("  SENSOR DATA  (Raspberry Pi output / your estimate)")
    print("-" * 60)
    duration_mins = _ask("Duration (minutes)",                  45.0, float)
    avg_hr        = _ask("Average heart rate (BPM)",           135.0, float)
    max_hr        = _ask("Max heart rate (BPM)",               165.0, float)
    hr_spikes     = _ask("HR spikes (count)",                    4,   int)
    pct_time_low  = _ask("% time in low HR zone (<100 BPM)",   12.0, float)
    avg_emg       = _ask("Average EMG activation (0-1000)",   480.0, float)
    emg_fatigue   = _ask("EMG fatigue % (first->last quarter drop)", 20.0, float)
    total_reps    = _ask("Total reps detected",                120,   int)

    return {
        'age':           age,
        'weight_kg':     weight_kg,
        'fitness_level': fitness_lvl,
        'workout_type':  workout_type,
        'athlete_type':  athlete_type,
        'body_fat_pct':  body_fat_pct,
        'limb_length':   limb_length,
        'duration_mins': duration_mins,
        'avg_hr':        avg_hr,
        'max_hr':        max_hr,
        'hr_spikes':     hr_spikes,
        'pct_time_low':  pct_time_low,
        'avg_emg':       avg_emg,
        'emg_fatigue':   emg_fatigue,
        'total_reps':    total_reps,
    }


# ---------------------------------------------------------------------------
#  6. QUICK PRESET SCENARIOS
# ---------------------------------------------------------------------------
PRESETS = {
    '1': {
        'name': 'Phone scrolling at gym (80 min, zero effort)',
        'data': {'age': 25, 'weight_kg': 80.0, 'fitness_level': 'medium',
                 'workout_type': 'hypertrophy', 'athlete_type': 'gym_bro',
                 'body_fat_pct': 15.0, 'limb_length': 'medium',
                 'duration_mins': 80, 'avg_hr': 82, 'max_hr': 100,
                 'hr_spikes': 0, 'pct_time_low': 92.0, 'avg_emg': 90,
                 'emg_fatigue': 1.5, 'total_reps': 30},
        'expected': 0,
    },
    '2': {
        'name': 'Light recovery day (25 min, gentle)',
        'data': {'age': 25, 'weight_kg': 80.0, 'fitness_level': 'medium',
                 'workout_type': 'hypertrophy', 'athlete_type': 'gym_bro',
                 'body_fat_pct': 15.0, 'limb_length': 'medium',
                 'duration_mins': 25, 'avg_hr': 98, 'max_hr': 118,
                 'hr_spikes': 1, 'pct_time_low': 50.0, 'avg_emg': 180,
                 'emg_fatigue': 5.0, 'total_reps': 50},
        'expected': 1,
    },
    '3': {
        'name': 'Solid gym session (45 min, good effort)',
        'data': {'age': 25, 'weight_kg': 80.0, 'fitness_level': 'medium',
                 'workout_type': 'hypertrophy', 'athlete_type': 'gym_bro',
                 'body_fat_pct': 15.0, 'limb_length': 'medium',
                 'duration_mins': 45, 'avg_hr': 135, 'max_hr': 165,
                 'hr_spikes': 4, 'pct_time_low': 12.0, 'avg_emg': 480,
                 'emg_fatigue': 20.0, 'total_reps': 120},
        'expected': 2,
    },
    '4': {
        'name': 'Full beast mode (60 min, everything maxed)',
        'data': {'age': 25, 'weight_kg': 85.0, 'fitness_level': 'high',
                 'workout_type': 'hypertrophy', 'athlete_type': 'hybrid',
                 'body_fat_pct': 12.0, 'limb_length': 'medium',
                 'duration_mins': 60, 'avg_hr': 155, 'max_hr': 185,
                 'hr_spikes': 9, 'pct_time_low': 4.0, 'avg_emg': 650,
                 'emg_fatigue': 35.0, 'total_reps': 200},
        'expected': 3,
    },
    '5': {
        'name': 'Heavy powerlifting (low HR, extreme EMG)',
        'data': {'age': 30, 'weight_kg': 100.0, 'fitness_level': 'high',
                 'workout_type': 'HILV', 'athlete_type': 'powerlifter',
                 'body_fat_pct': 20.0, 'limb_length': 'short',
                 'duration_mins': 40, 'avg_hr': 92, 'max_hr': 115,
                 'hr_spikes': 1, 'pct_time_low': 68.0, 'avg_emg': 580,
                 'emg_fatigue': 28.0, 'total_reps': 60},
        'expected': 3,
    },
    '6': {
        'name': 'EC-01 Edge case: distracted vs light recovery (label=Low)',
        'data': {'age': 28, 'weight_kg': 80.0, 'fitness_level': 'medium',
                 'workout_type': 'hypertrophy', 'athlete_type': 'gym_bro',
                 'body_fat_pct': 18.0, 'limb_length': 'medium',
                 'duration_mins': 38, 'avg_hr': 87, 'max_hr': 105,
                 'hr_spikes': 1, 'pct_time_low': 72.0, 'avg_emg': 155,
                 'emg_fatigue': 3.5, 'total_reps': 48},
        'expected': 0,
    },
}


# ---------------------------------------------------------------------------
#  7. MAIN LOOP
# ---------------------------------------------------------------------------
def main():
    print()
    print("+" + "=" * 58 + "+")
    print("|   WORKOUT EFFECTIVENESS -- Manual Tester               |")
    print("|   Model accuracy: 96.1%  |  4 Labels: Low->Maximum     |")
    print("+" + "=" * 58 + "+")

    while True:
        print()
        print("  MENU")
        print("  " + "-" * 52)
        print("  [1]  Enter my own workout values")
        print("  [2]  Run a quick preset scenario")
        print("  [q]  Quit")
        print()

        choice = input("  Choice: ").strip().lower()

        if choice == 'q':
            print("\n  Goodbye!\n")
            break

        elif choice == '1':
            print("\n  Press Enter to accept the default value shown in [brackets].\n")
            workout = collect_workout()
            print("\n  Analyzing your workout...")
            result = predict_and_explain(workout)
            print_result(result)

        elif choice == '2':
            print()
            print("  PRESET SCENARIOS")
            print("  " + "-" * 52)
            for k, p in PRESETS.items():
                exp = LABEL_NAMES[p['expected']]
                print(f"  [{k}]  {p['name']}")
                print(f"         expected: {exp}")
            print("  [b]  Back to main menu")
            print()

            preset_choice = input("  Select preset: ").strip()
            if preset_choice == 'b':
                continue
            if preset_choice not in PRESETS:
                print("  ! Unknown preset.")
                continue

            p = PRESETS[preset_choice]
            print(f"\n  Running: {p['name']}")
            print("  Analyzing...")
            result = predict_and_explain(p['data'])

            expected   = p['expected']
            match_str  = "PASS" if result['label'] == expected \
                         else f"FAIL  (expected: {LABEL_NAMES[expected]})"
            print(f"\n  Prediction vs expected: {match_str}")
            print_result(result)

        else:
            print("  ! Unknown option. Type 1, 2, or q.")


if __name__ == "__main__":
    main()
