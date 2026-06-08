import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from AI.test_model import predict_and_explain, LABEL_NAMES

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

print('\n' + '='*100)
print('  WORKOUT EFFECTIVENESS - DEMO SCENARIO VALIDATION')
print('='*100)

correct = 0
count = 0

for scenario in demo_scenarios:
    count += 1
    scenario_name = scenario['name']
    print(f'\n  Running: {scenario_name}')
    
    # Run prediction
    result = predict_and_explain(scenario['data'])
    
    expected = scenario['expected']
    actual = result['label']
    label_name = result['label_name']
    confidence = result['confidence'] * 100
    
    factors = [f['description'] for f in result['top_factors']]
    explanation = " | ".join(factors)
    
    match = 'PASS' if expected == actual else 'MISS'
    if match == 'PASS': correct += 1
    
    print(f'  [{match}] Expected: {expected} ({LABEL_NAMES[expected]:<8}) | Predicted: {actual} ({label_name:<8})')
    print(f'         Confidence: {confidence:.1f}%')
    print(f'         Key Factors: {explanation}')

print('\n' + '='*100)
print(f'  Validation Summary: {correct}/{count} scenarios predicted correctly.')
print('='*100 + '\n')
