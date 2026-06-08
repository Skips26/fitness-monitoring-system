"""
=============================================================================
  WORKOUT EFFECTIVENESS MODEL  —  Training Pipeline
  ──────────────────────────────────────────────────
  Trains an XGBoost multi-class classifier on synthetic gym workout data
  to predict workout effectiveness (0=Low, 1=Moderate, 2=High, 3=Maximum).

  Designed to run on Kaggle.  Upload synthetic_workouts.csv as a dataset,
  then run this notebook/script. Not needed anymore****

  Pipeline:
      1. Load & explore data
      2. Preprocessing (drop workout_id, train/test split)
      3. Hyperparameter tuning via RandomizedSearchCV
      4. Train final model
      5. Evaluate (confusion matrix, classification report)
      6. Feature importance
      7. SHAP explainability (per-prediction "why" explanations)
      8. Export model + explanation function for web deployment

  Model choice: XGBoost
      - Best-in-class for tabular data with non-linear conditional rules
      - Natively handles conditional thresholds (e.g., "IF high intensity
        AND short duration THEN Low")
      - TreeSHAP provides exact per-prediction explanations
      - No feature scaling required
      - Fast training on small datasets (6000 samples)
=============================================================================
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, StratifiedKFold, RandomizedSearchCV
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score,
    f1_score, ConfusionMatrixDisplay
)
from scipy.stats import uniform, randint

import xgboost as xgb
import shap
import joblib

warnings.filterwarnings('ignore')
matplotlib.rcParams['figure.dpi'] = 120

#  1. CONFIGURATION

# Auto-detect environment (Kaggle vs local)
if os.path.exists('/kaggle/input'):
    # ── Kaggle ───────────────────────────────────────────────────────────
    # Update 'workout-dataset' to match your Kaggle dataset name
    DATA_PATH   = '/kaggle/input/workout-dataset/synthetic_workouts.csv'
    OUTPUT_DIR  = '/kaggle/working'
    print("[ENV] Running on Kaggle")
else:
    # ── Local ────────────────────────────────────────────────────────────
    SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
    DATA_PATH   = os.path.join(SCRIPT_DIR, 'synthetic_workouts.csv')
    OUTPUT_DIR  = SCRIPT_DIR
    print("[ENV] Running locally")

LABEL_NAMES   = {0: 'Low', 1: 'Moderate', 2: 'High', 3: 'Maximum'}
RANDOM_STATE  = 42
TEST_SIZE     = 0.2   # 80/20 train/test split

# Features the Raspberry Pi hardware provides + Demographic Context
FEATURE_COLS = [
    'age', 'weight_kg', 'fitness_level', 'workout_type', 'athlete_type', 'body_fat_pct', 'limb_length',
    'duration_mins', 'avg_hr', 'max_hr', 'hr_spikes',
    'pct_time_low', 'avg_emg', 'emg_fatigue', 'total_reps'
]
TARGET_COL = 'effectiveness_label'


#  2. LOAD & EXPLORE DATA

print("\n" + "=" * 62)
print("  STEP 1: Loading dataset")
print("=" * 62)

df = pd.read_csv(DATA_PATH)

print(f"\n  Shape:    {df.shape}")
print(f"  Features: {list(df.columns)}")
print(f"\n  Class distribution:")
for label in sorted(df[TARGET_COL].unique()):
    count = len(df[df[TARGET_COL] == label])
    pct = count / len(df) * 100
    print(f"    {label} ({LABEL_NAMES[label]:>8s}):  {count}  ({pct:.1f}%)")

print(f"\n  First 5 rows:")
print(df.head().to_string())

print(f"\n  Feature statistics:")
print(df[FEATURE_COLS].describe().round(2).to_string())

#  3. PREPROCESSING

print("\n" + "=" * 62)
print("  STEP 2: Preprocessing")
print("=" * 62)

# Convert categorical columns to 'category' dtype for XGBoost
CATEGORICAL_COLS = ['fitness_level', 'workout_type', 'athlete_type', 'limb_length']
for col in CATEGORICAL_COLS:
    df[col] = df[col].astype('category')

# Drop workout_id (not a training feature)
X = df[FEATURE_COLS].copy()
y = df[TARGET_COL].copy()

print(f"\n  X shape: {X.shape}  (dropped workout_id)")
print(f"  y shape: {y.shape}")

# Stratified train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y
)

print(f"\n  Train set: {X_train.shape[0]} samples")
print(f"  Test set:  {X_test.shape[0]} samples")
print(f"\n  Train class distribution:")
for label in sorted(y_train.unique()):
    count = (y_train == label).sum()
    print(f"    {label} ({LABEL_NAMES[label]:>8s}):  {count}")

# Check for missing values
missing = X.isnull().sum().sum()
print(f"\n  Missing values: {missing}")

#  4. HYPERPARAMETER TUNING (RandomizedSearchCV)

# optimization technique: RandomizedSearchCV to find the best hyperparameters for XGBoost

print("\n" + "=" * 62)
print("  STEP 3: Hyperparameter Tuning (RandomizedSearchCV)")
print("=" * 62)

# Define the parameter search space
param_distributions = {
    'n_estimators':     randint(100, 600),
    'max_depth':        randint(4, 12),
    'learning_rate':    uniform(0.03, 0.27),     # 0.03 to 0.30
    'min_child_weight': randint(1, 7),
    'subsample':        uniform(0.7, 0.3),       # 0.7 to 1.0
    'colsample_bytree': uniform(0.3, 0.4),       # 0.3 to 0.7
    'gamma':            uniform(0, 0.3),          # 0 to 0.3
    'reg_alpha':        uniform(0, 0.5),          # L1 regularization
    'reg_lambda':       uniform(0.5, 1.5),        # L2 regularization
}

# Base estimator
base_model = xgb.XGBClassifier(
    objective='multi:softprob',
    num_class=4,
    enable_categorical=True,
    eval_metric='mlogloss',
    random_state=RANDOM_STATE,
    tree_method='hist',   # fast training
)

# Randomized search with 5-fold stratified CV
search = RandomizedSearchCV(
    estimator=base_model,
    param_distributions=param_distributions,
    n_iter=50,
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
    scoring='f1_macro',
    random_state=RANDOM_STATE,
    n_jobs=-1,
    verbose=1,
)

print("\n  Searching 50 random hyperparameter combinations (5-fold CV)...")
search.fit(X_train, y_train)

print(f"\n  Best CV F1 (macro): {search.best_score_:.4f}")
print(f"  Best parameters:")
for param, value in search.best_params_.items():
    if isinstance(value, float):
        print(f"    {param:22s}: {value:.4f}")
    else:
        print(f"    {param:22s}: {value}")


#  5. TRAIN FINAL MODEL WITH BEST PARAMETERS

print("\n" + "=" * 62)
print("  STEP 4: Training Final Model")
print("=" * 62)

best_model = search.best_estimator_

# Re-fit on full training set (already done by RandomizedSearchCV, but explicit)
best_model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False,
)

# Predictions
y_pred = best_model.predict(X_test)
y_pred_proba = best_model.predict_proba(X_test)

accuracy = accuracy_score(y_test, y_pred)
f1_macro = f1_score(y_test, y_pred, average='macro')

print(f"\n  Test Accuracy:    {accuracy:.4f}  ({accuracy * 100:.1f}%)")
print(f"  Test F1 (macro):  {f1_macro:.4f}")


#  6. CLASSIFICATION REPORT


print("\n" + "=" * 62)
print("  STEP 5: Classification Report")
print("=" * 62)

target_names = [f"{i} ({LABEL_NAMES[i]})" for i in sorted(LABEL_NAMES.keys())]
report = classification_report(y_test, y_pred, target_names=target_names)
print(f"\n{report}")


#  7. CONFUSION MATRIX VISUALIZATION

print("  STEP 6: Confusion Matrix")
print("=" * 62)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Raw counts
cm = confusion_matrix(y_test, y_pred)
disp1 = ConfusionMatrixDisplay(cm, display_labels=[LABEL_NAMES[i] for i in range(4)])
disp1.plot(ax=axes[0], cmap='Blues', values_format='d')
axes[0].set_title('Confusion Matrix (Counts)', fontsize=14, fontweight='bold')

# Normalized (percentages)
cm_norm = confusion_matrix(y_test, y_pred, normalize='true')
disp2 = ConfusionMatrixDisplay(cm_norm, display_labels=[LABEL_NAMES[i] for i in range(4)])
disp2.plot(ax=axes[1], cmap='Greens', values_format='.2%')
axes[1].set_title('Confusion Matrix (Normalized)', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'confusion_matrix.png'), bbox_inches='tight')
plt.show()
print(f"  Saved: confusion_matrix.png")

#  8. FEATURE IMPORTANCE



# importance in training dataset. I need to know what feature contribute the most to the model performance
# so that i can prioritize what is actually important in my system


print("\n" + "=" * 62)
print("  STEP 7: Feature Importance")
print("=" * 62)

importances = best_model.feature_importances_
feat_imp = pd.DataFrame({
    'Feature': FEATURE_COLS,
    'Importance': importances
}).sort_values('Importance', ascending=True)

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(feat_imp['Feature'], feat_imp['Importance'], color='#2196F3', edgecolor='#1565C0')
ax.set_xlabel('Importance (Gain)', fontsize=12)
ax.set_title('XGBoost Feature Importance', fontsize=14, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Add value labels
for bar, val in zip(bars, feat_imp['Importance']):
    ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
            f'{val:.3f}', va='center', fontsize=10)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'feature_importance.png'), bbox_inches='tight')
plt.show()

print("\n  Feature importance ranking:")
for _, row in feat_imp.iloc[::-1].iterrows():
    print(f"    {row['Feature']:18s}:  {row['Importance']:.4f}")


#  9. SHAP EXPLAINABILITY


# SHAP explanation: tells us why the model predicted a certain effectiveness label for a certain workout
# it gives us a "per-prediction" explanation, which is much more useful than the global feature importance
# it tells us which features pushed the prediction higher or lower from the base rate

print("\n" + "=" * 62)
print("  STEP 8: SHAP Explainability")
print("=" * 62)

# Create SHAP explainer (TreeSHAP — exact and fast for tree models)
try:
    explainer = shap.TreeExplainer(best_model)
except ValueError:
    # Workaround for XGBoost > 2.0 multi-class base_score array format with SHAP
    import shap.explainers._tree
    import ast
    original_decode = shap.explainers._tree.decode_ubjson_buffer
    
    def patched_decode(*args, **kwargs):
        jmodel = original_decode(*args, **kwargs)
        base_score = jmodel.get("learner", {}).get("learner_model_param", {}).get("base_score", "")
        if isinstance(base_score, str) and base_score.startswith('['):
            scores = ast.literal_eval(base_score.replace('E', 'e'))
            jmodel["learner"]["learner_model_param"]["base_score"] = str(scores[0])
        return jmodel
        
    shap.explainers._tree.decode_ubjson_buffer = patched_decode
    explainer = shap.TreeExplainer(best_model)

shap_values = explainer.shap_values(X_test)

# Handle different output structures of SHAP versions
if isinstance(shap_values, list):
    shap_vals_list = shap_values
elif isinstance(shap_values, np.ndarray) and len(shap_values.shape) == 3:
    if shap_values.shape[2] == 4:
        shap_vals_list = [shap_values[:, :, c] for c in range(4)]
    else:
        shap_vals_list = [shap_values[:, c, :] for c in range(4)]
else:
    try:
        vals = shap_values.values if hasattr(shap_values, 'values') else shap_values
        if len(vals.shape) == 3:
            if vals.shape[2] == 4:
                shap_vals_list = [vals[:, :, c] for c in range(4)]
            else:
                shap_vals_list = [vals[:, c, :] for c in range(4)]
        else:
            shap_vals_list = [vals]
    except Exception:
        shap_vals_list = shap_values

# SHAP summary plot (bee swarm) — shows feature impact per class
print("\n  Generating SHAP summary plot...")
fig, axes = plt.subplots(2, 2, figsize=(18, 14))
for i, ax in enumerate(axes.flat):
    plt.sca(ax)
    shap.summary_plot(
        shap_vals_list[i], X_test,
        plot_type='dot',
        show=False,
        plot_size=None,
    )
    ax.set_title(f'Class {i}: {LABEL_NAMES[i]}', fontsize=13, fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'shap_summary.png'), bbox_inches='tight')
plt.show()
print(f"  Saved: shap_summary.png")

# SHAP bar plot — mean absolute SHAP values
print("\n  Generating SHAP global importance plot...")
fig = plt.figure(figsize=(10, 6))
shap.summary_plot(shap_vals_list, X_test, plot_type='bar',
                  class_names=[LABEL_NAMES[i] for i in range(4)],
                  show=False)
plt.title('SHAP Feature Importance (Mean |SHAP|)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'shap_importance.png'), bbox_inches='tight')
plt.show()
print(f"  Saved: shap_importance.png")


#  10. HUMAN-READABLE EXPLANATION FUNCTION

# Feature descriptions for generating natural-language explanations
FEATURE_DESCRIPTIONS = {
    'age': {
        'positive': 'age ({} yrs)',
        'negative': 'age ({} yrs)',
    },
    'weight_kg': {
        'positive': 'high body weight ({:.1f} kg)',
        'negative': 'low body weight ({:.1f} kg)',
    },
    'fitness_level': {
        'positive': 'fitness level ({})',
        'negative': 'fitness level ({})',
    },
    'workout_type': {
        'positive': 'workout type ({})',
        'negative': 'workout type ({})',
    },
    'athlete_type': {
        'positive': 'athlete type ({})',
        'negative': 'athlete type ({})',
    },
    'body_fat_pct': {
        'positive': 'body fat ({:.1f}%)',
        'negative': 'body fat ({:.1f}%)',
    },
    'limb_length': {
        'positive': 'limb length ({})',
        'negative': 'limb length ({})',
    },
    'duration_mins': {
        'positive': 'long session duration ({:.0f} min)',
        'negative': 'short session duration ({:.0f} min)',
    },
    'avg_hr': {
        'positive': 'elevated average heart rate ({:.0f} BPM)',
        'negative': 'low average heart rate ({:.0f} BPM)',
    },
    'max_hr': {
        'positive': 'high peak heart rate ({:.0f} BPM)',
        'negative': 'low peak heart rate ({:.0f} BPM)',
    },
    'hr_spikes': {
        'positive': 'frequent HR spikes ({})',
        'negative': 'few HR spikes ({})',
    },
    'pct_time_low': {
        'positive': 'significant time in low HR zone ({:.1f}%)',
        'negative': 'minimal time in low HR zone ({:.1f}%)',
    },
    'avg_emg': {
        'positive': 'strong muscle engagement (EMG: {:.0f})',
        'negative': 'weak muscle engagement (EMG: {:.0f})',
    },
    'emg_fatigue': {
        'positive': 'significant muscle fatigue ({:.1f}%)',
        'negative': 'minimal muscle fatigue ({:.1f}%)',
    },
    'total_reps': {
        'positive': 'high rep count ({})',
        'negative': 'low rep count ({})',
    },
}


def explain_prediction(model, explainer_obj, sample, top_k=3):
    """
    Predict workout effectiveness and generate a human-readable explanation.

    Parameters:
        model:          trained XGBoost model
        explainer_obj:  SHAP TreeExplainer instance
        sample:         dict or pd.Series with the 8 features
        top_k:          number of top reasons to include

    Returns:
        dict with 'label', 'label_name', 'confidence', 'probabilities',
        'explanation', 'top_factors'
    """
    # Prepare input
    if isinstance(sample, pd.DataFrame):
        sample_df = sample.copy()
    else:
        sample_df = pd.DataFrame([sample], columns=FEATURE_COLS)

    # Convert categoricals to 'category' dtype
    categorical_cols = ['fitness_level', 'workout_type', 'athlete_type', 'limb_length']
    for col in categorical_cols:
        if col in sample_df.columns:
            sample_df[col] = sample_df[col].astype('category')

    # Predict
    pred_label = int(model.predict(sample_df)[0])
    pred_proba = model.predict_proba(sample_df)[0]
    confidence = float(pred_proba[pred_label])

    # SHAP values for the predicted class
    shap_vals = explainer_obj.shap_values(sample_df)
    if isinstance(shap_vals, list):
        shap_for_class = shap_vals[pred_label][0]
    else:
        if len(shap_vals.shape) == 3:
            if shap_vals.shape[2] == 4:
                shap_for_class = shap_vals[0, :, pred_label]
            else:
                shap_for_class = shap_vals[0, pred_label, :]
        else:
            shap_for_class = shap_vals[0]  # shape: (n_features,)

    # Rank features by absolute SHAP contribution
    feat_shap = list(zip(FEATURE_COLS, shap_for_class, sample_df.iloc[0]))
    feat_shap.sort(key=lambda x: abs(x[1]), reverse=True)

    # Build explanation text
    top_factors = []
    for feat_name, shap_val, feat_val in feat_shap[:top_k]:
        direction = 'positive' if shap_val > 0 else 'negative'
        desc_template = FEATURE_DESCRIPTIONS[feat_name][direction]
        desc = desc_template.format(feat_val)
        top_factors.append({
            'feature': feat_name,
            'value': feat_val,
            'shap_value': float(shap_val),
            'description': desc,
        })

    # Compose natural language
    reasons = [f['description'] for f in top_factors]
    explanation = (
        f"{LABEL_NAMES[pred_label]} effectiveness "
        f"(confidence: {confidence:.0%}). "
        f"Key factors: {'; '.join(reasons)}."
    )

    return {
        'label': pred_label,
        'label_name': LABEL_NAMES[pred_label],
        'confidence': round(confidence, 4),
        'probabilities': {
            LABEL_NAMES[i]: round(float(pred_proba[i]), 4)
            for i in range(4)
        },
        'explanation': explanation,
        'top_factors': top_factors,
    }


#  11. DEMO: EXPLAIN EDGE-CASE PREDICTIONS

print("\n" + "=" * 62)
print("  STEP 9: Prediction + Explanation Demo")
print("=" * 62)

# Test with the original labeled scenarios
demo_scenarios = [
    {
        'name': 'Ultra-short burst (3 min, extreme intensity)',
        'data': {'age': 25, 'weight_kg': 80.0, 'fitness_level': 'medium', 'workout_type': 'hypertrophy', 'athlete_type': 'hybrid', 'body_fat_pct': 15.0, 'limb_length': 'medium', 'duration_mins': 3, 'avg_hr': 170, 'max_hr': 190,
                 'hr_spikes': 8, 'pct_time_low': 0.0, 'avg_emg': 700,
                 'emg_fatigue': 40.0, 'total_reps': 25},
        'expected': 0,
    },
    {
        'name': 'Phone scrolling (80 min, zero effort)',
        'data': {'age': 25, 'weight_kg': 80.0, 'fitness_level': 'medium', 'workout_type': 'hypertrophy', 'athlete_type': 'hybrid', 'body_fat_pct': 15.0, 'limb_length': 'medium', 'duration_mins': 80, 'avg_hr': 82, 'max_hr': 100,
                 'hr_spikes': 0, 'pct_time_low': 92.0, 'avg_emg': 90,
                 'emg_fatigue': 1.5, 'total_reps': 30},
        'expected': 0,
    },
    {
        'name': 'Solid bodyweight workout (45 min)',
        'data': {'age': 25, 'weight_kg': 80.0, 'fitness_level': 'medium', 'workout_type': 'hypertrophy', 'athlete_type': 'hybrid', 'body_fat_pct': 15.0, 'limb_length': 'medium', 'duration_mins': 45, 'avg_hr': 135, 'max_hr': 165,
                 'hr_spikes': 4, 'pct_time_low': 12.0, 'avg_emg': 480,
                 'emg_fatigue': 20.0, 'total_reps': 120},
        'expected': 2,
    },
    {
        'name': 'Full beast mode (60 min, everything maxed)',
        'data': {'age': 25, 'weight_kg': 80.0, 'fitness_level': 'medium', 'workout_type': 'hypertrophy', 'athlete_type': 'hybrid', 'body_fat_pct': 15.0, 'limb_length': 'medium', 'duration_mins': 60, 'avg_hr': 155, 'max_hr': 185,
                 'hr_spikes': 9, 'pct_time_low': 4.0, 'avg_emg': 650,
                 'emg_fatigue': 35.0, 'total_reps': 200},
        'expected': 3,
    },
    {
        'name': 'Heavy powerlifting (low HR, extreme EMG)',
        'data': {'age': 30, 'weight_kg': 100.0, 'fitness_level': 'high', 'workout_type': 'HILV', 'athlete_type': 'powerlifter', 'body_fat_pct': 20.0, 'limb_length': 'short', 'duration_mins': 40, 'avg_hr': 92, 'max_hr': 115,
                 'hr_spikes': 1, 'pct_time_low': 68.0, 'avg_emg': 580,
                 'emg_fatigue': 28.0, 'total_reps': 60},
        'expected': 3,
    },
    {
        'name': 'Average gym session (40 min)',
        'data': {'age': 25, 'weight_kg': 80.0, 'fitness_level': 'medium', 'workout_type': 'hypertrophy', 'athlete_type': 'hybrid', 'body_fat_pct': 15.0, 'limb_length': 'medium', 'duration_mins': 40, 'avg_hr': 118, 'max_hr': 142,
                 'hr_spikes': 2, 'pct_time_low': 28.0, 'avg_emg': 340,
                 'emg_fatigue': 12.0, 'total_reps': 90},
        'expected': 1,
    },
]

#some automated testing.

correct = 0
total = len(demo_scenarios)

for scenario in demo_scenarios:
    result = explain_prediction(best_model, explainer, scenario['data'])
    match = "PASS" if result['label'] == scenario['expected'] else "MISS"
    if result['label'] == scenario['expected']:
        correct += 1

    print(f"\n  [{match}] {scenario['name']}")
    print(f"    Expected: {scenario['expected']} ({LABEL_NAMES[scenario['expected']]})")
    print(f"    Got:      {result['label']} ({result['label_name']})")
    print(f"    Explanation: {result['explanation']}")
    print(f"    Probabilities: {result['probabilities']}")

print(f"\n  Demo accuracy: {correct}/{total} scenarios predicted correctly")


#  12. SAVE MODEL & ARTIFACTS FOR DEPLOYMENT

print("\n" + "=" * 62)
print("  STEP 10: Saving Model & Artifacts")
print("=" * 62)

# Save XGBoost model (native JSON format — portable)
model_json_path = os.path.join(OUTPUT_DIR, 'workout_model.json')
best_model.save_model(model_json_path)
print(f"  Saved XGBoost model:     {model_json_path}")

# Save with joblib (includes sklearn wrapper metadata)
model_joblib_path = os.path.join(OUTPUT_DIR, 'workout_model.joblib')
joblib.dump(best_model, model_joblib_path)
print(f"  Saved joblib model:      {model_joblib_path}")

# Save model config (features, labels, best params) as JSON
config = {
    'feature_columns': FEATURE_COLS,
    'target_column': TARGET_COL,
    'label_names': LABEL_NAMES,
    'best_params': {k: (int(v) if isinstance(v, (np.integer,)) else
                        float(v) if isinstance(v, (np.floating,)) else v)
                    for k, v in search.best_params_.items()},
    'test_accuracy': float(accuracy),
    'test_f1_macro': float(f1_macro),
    'feature_descriptions': FEATURE_DESCRIPTIONS,
}

config_path = os.path.join(OUTPUT_DIR, 'model_config.json')
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print(f"  Saved model config:      {config_path}")

print("\n" + "=" * 62)
print("  TRAINING COMPLETE")
print("=" * 62)
print(f"\n  Final Test Accuracy:  {accuracy:.4f}  ({accuracy * 100:.1f}%)")
print(f"  Final Test F1 Macro:  {f1_macro:.4f}")
print()
print("  Exported files:")
print(f"    - workout_model.json      (XGBoost native, for deployment)")
print(f"    - workout_model.joblib    (sklearn wrapper, for Python)")
print(f"    - model_config.json       (features, labels, params)")
print(f"    - confusion_matrix.png")
print(f"    - feature_importance.png")
print(f"    - shap_summary.png")
print(f"    - shap_importance.png")
print()
print("  To use in your web app:")
print("    model = xgb.XGBClassifier()")
print("    model.load_model('workout_model.json')")
print("    prediction = model.predict(your_workout_features)")
print()
