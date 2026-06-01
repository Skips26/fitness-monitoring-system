#!/usr/bin/env python3
"""
=============================================================================
  SYNTHETIC GYM WORKOUT DATA GENERATOR  (v4)
  ───────────────────────────────────────────
  Generates a balanced, gym-specific dataset for training a workout
  effectiveness classification model.

  Features (Raspberry Pi hardware + user-profile demographics):
      workout_id     – auto-generated UUID  (dropped before training)
      weight_kg      – body weight in kilograms  (from user profile)
      duration_mins  – length of workout in minutes
      avg_hr         – average heart rate (BPM)
      max_hr         – maximum heart rate (BPM)
      hr_spikes      – count of sudden HR jumps (>20 BPM between readings)
      pct_time_low   – % of workout time spent in "low" HR zone (<100 BPM)
      avg_emg        – average EMG activation level (0-1000 scale)
      emg_fatigue    – fatigue index: % drop from first to last quarter
      total_reps     – repetitions detected by MPU6050 accelerometer
      effectiveness_label – target (0=Low, 1=Moderate, 2=High, 3=Maximum)

  Labels:
      0 = Low         (too short, phone scrolling, going through motions)
      1 = Moderate     (light recovery, average session, short but decent)
      2 = High         (solid bodyweight, intense shorter, good gym session)
      3 = Maximum      (full beast mode, heavy powerlifting, high-rep endurance)

  Dataset: ~18000 base samples (4500/class, 27 sub-profiles) × 2.5 scale
            + ~2400 edge-case samples (8 interpolated profiles × 300)
            Grand total ≈ 51 000 samples
=============================================================================
"""

import numpy as np
import pandas as pd
import uuid
import os

# ── Reproducibility ──────────────────────────────────────────────────────────
np.random.seed(42)

# ── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "synthetic_workouts.csv")


# =============================================================================
#  SUB-PROFILE DEFINITIONS  (27 total across 4 classes)
# =============================================================================
#
# Each profile defines uniform sampling ranges for every feature.
# Physical constraints are enforced post-sampling.
#
# Design philosophy (from 15 user-labeled gym scenarios):
#   - Duration < ~12 min  -> Low, regardless of intensity
#   - Duration 12-20 min  -> Low<->Moderate, gated by emg_fatigue
#   - Long duration + no effort -> Low (phone scrolling at gym)
#   - Heavy powerlifting (low HR, extreme EMG, long rests) -> can be Maximum
#   - High-rep endurance (moderate EMG, extreme volume) -> can be Maximum
#   - HR spikes differentiate powerlifting High vs Maximum
#   - avg_emg differentiates Moderate vs High for ~30 min sessions
#   - Overall intensity differentiates High vs Maximum for ~35 min sessions

PROFILES = {

    # =================================================================
    #  LABEL 0: LOW EFFECTIVENESS  (4500 samples, 8 sub-profiles)
    # =================================================================
    0: [
        {
            # Ultra-short burst: extreme intensity, way too short.
            # Even max effort can't save a 2-12 minute "workout".
            'name': 'ultra_short_burst',
            'count': 600,
            'duration_mins':  (2, 12),
            'avg_hr':         (120, 175),
            'max_hr_delta':   (15, 35),
            'hr_spikes':      (2, 9),
            'pct_time_low':   (0, 10),
            'avg_emg':        (300, 700),
            'emg_fatigue':    (10, 40),
            'total_reps':     (10, 80),
        },
        {
            # Phone scrolling: 40-90 min at the gym but barely lifting.
            # Time alone does not equal effectiveness.
            'name': 'phone_scrolling',
            'count': 600,
            'duration_mins':  (40, 90),
            'avg_hr':         (65, 92),
            'max_hr_delta':   (8, 22),
            'hr_spikes':      (0, 1),
            'pct_time_low':   (70, 96),
            'avg_emg':        (30, 180),
            'emg_fatigue':    (0, 4),
            'total_reps':     (8, 60),
        },
        {
            # Short and lazy: low duration AND low effort.
            # Did one or two easy sets and bounced.
            'name': 'short_lazy',
            'count': 525,
            'duration_mins':  (5, 18),
            'avg_hr':         (72, 105),
            'max_hr_delta':   (8, 20),
            'hr_spikes':      (0, 2),
            'pct_time_low':   (45, 92),
            'avg_emg':        (40, 190),
            'emg_fatigue':    (0, 5),
            'total_reps':     (5, 40),
        },
        {
            # Medium duration, halfhearted: 20-35 min but barely engaging
            # muscles. Going through the motions with zero push.
            'name': 'medium_halfhearted',
            'count': 525,
            'duration_mins':  (20, 38),
            'avg_hr':         (70, 98),
            'max_hr_delta':   (8, 20),
            'hr_spikes':      (0, 2),
            'pct_time_low':   (55, 90),
            'avg_emg':        (50, 180),
            'emg_fatigue':    (0, 5),
            'total_reps':     (15, 55),
        },
        {
            # Short heavy singles: walks in, does 2-3 heavy singles
            # (extremely high EMG) and leaves after 3-10 min.
            # Impressive weight, but not a workout.
            'name': 'short_heavy_singles',
            'count': 525,
            'duration_mins':  (3, 10),
            'avg_hr':         (100, 140),
            'max_hr_delta':   (20, 40),
            'hr_spikes':      (1, 5),
            'pct_time_low':   (5, 40),
            'avg_emg':        (500, 750),
            'emg_fatigue':    (5, 20),
            'total_reps':     (3, 15),
        },
        {
            # Distracted gym: shows up for 25-50 min but is constantly
            # resting, chatting, inconsistent. Sporadic effort bursts.
            'name': 'distracted_gym',
            'count': 600,
            'duration_mins':  (25, 55),
            'avg_hr':         (75, 100),
            'max_hr_delta':   (10, 28),
            'hr_spikes':      (0, 3),
            'pct_time_low':   (55, 88),
            'avg_emg':        (80, 220),
            'emg_fatigue':    (1, 7),
            'total_reps':     (20, 65),
        },
        {
            # Fidgeting/light movement: extremely high reps but zero intensity.
            # Simulates restless leg, playing around, etc.
            'name': 'fidgeting_high_reps',
            'count': 525,
            'duration_mins':  (20, 90),
            'avg_hr':         (65, 85),
            'max_hr_delta':   (5, 15),
            'hr_spikes':      (0, 1),
            'pct_time_low':   (80, 95),
            'avg_emg':        (30, 80),
            'emg_fatigue':    (0, 2),
            'total_reps':     (100, 250),
        },
        {
            # Warmup-only: light movement for 3-12 min, stretching,
            # foam rolling, a few bodyweight reps. Never gets going.
            'name': 'warmup_only',
            'count': 600,
            'duration_mins':  (3, 14),
            'avg_hr':         (70, 100),
            'max_hr_delta':   (5, 18),
            'hr_spikes':      (0, 1),
            'pct_time_low':   (50, 95),
            'avg_emg':        (30, 150),
            'emg_fatigue':    (0, 3),
            'total_reps':     (5, 30),
        },
    ],

    # =================================================================
    #  LABEL 1: MODERATE EFFECTIVENESS  (4500 samples, 7 sub-profiles)
    # =================================================================
    1: [
        {
            # Light recovery: gentle bodyweight, easy stretching with
            # movement. Active recovery day, 20-35 min.
            'name': 'light_recovery',
            'count': 675,
            'duration_mins':  (20, 35),
            'avg_hr':         (85, 112),
            'max_hr_delta':   (10, 25),
            'hr_spikes':      (0, 2),
            'pct_time_low':   (38, 62),
            'avg_emg':        (110, 270),
            'emg_fatigue':    (2, 9),
            'total_reps':     (30, 75),
        },
        {
            # Typical average gym session: 30-48 min, moderate effort,
            # nothing extreme. The "I did my thing" workout.
            'name': 'average_session',
            'count': 675,
            'duration_mins':  (30, 48),
            'avg_hr':         (105, 130),
            'max_hr_delta':   (12, 25),
            'hr_spikes':      (1, 4),
            'pct_time_low':   (18, 40),
            'avg_emg':        (230, 390),
            'emg_fatigue':    (7, 16),
            'total_reps':     (50, 105),
        },
        {
            # Moderate quick: 22-35 min with moderate pace. Could be
            # High if muscle activation were stronger.
            'name': 'moderate_quick',
            'count': 600,
            'duration_mins':  (22, 35),
            'avg_hr':         (110, 135),
            'max_hr_delta':   (14, 28),
            'hr_spikes':      (1, 4),
            'pct_time_low':   (15, 38),
            'avg_emg':        (240, 370),
            'emg_fatigue':    (7, 15),
            'total_reps':     (50, 95),
        },
        {
            # Short but decent: 13-22 min with enough fatigue to tip
            # from Low into Moderate. emg_fatigue is the gating feature.
            'name': 'short_decent',
            'count': 525,
            'duration_mins':  (13, 22),
            'avg_hr':         (115, 145),
            'max_hr_delta':   (15, 30),
            'hr_spikes':      (2, 5),
            'pct_time_low':   (5, 25),
            'avg_emg':        (320, 500),
            'emg_fatigue':    (11, 22),
            'total_reps':     (40, 75),
        },
        {
            # Long but easy: 35-55 min at low intensity. Puts in the
            # time but doesn't push. Slightly better than "distracted".
            'name': 'long_easy',
            'count': 675,
            'duration_mins':  (35, 55),
            'avg_hr':         (90, 115),
            'max_hr_delta':   (10, 22),
            'hr_spikes':      (0, 2),
            'pct_time_low':   (35, 58),
            'avg_emg':        (170, 320),
            'emg_fatigue':    (4, 12),
            'total_reps':     (50, 95),
        },
        {
            # Beginner cautious: 25-40 min, learning form, light weight,
            # moderate EMG because muscles are engaged but not maxed.
            'name': 'beginner_cautious',
            'count': 675,
            'duration_mins':  (25, 42),
            'avg_hr':         (95, 125),
            'max_hr_delta':   (12, 25),
            'hr_spikes':      (0, 3),
            'pct_time_low':   (20, 48),
            'avg_emg':        (180, 340),
            'emg_fatigue':    (5, 14),
            'total_reps':     (40, 90),
        },
        {
            # Single muscle focus: 20-35 min targeting one group (e.g.,
            # only arms). Decent engagement but limited scope.
            'name': 'single_muscle_focus',
            'count': 675,
            'duration_mins':  (20, 35),
            'avg_hr':         (100, 128),
            'max_hr_delta':   (12, 25),
            'hr_spikes':      (1, 3),
            'pct_time_low':   (20, 45),
            'avg_emg':        (250, 420),
            'emg_fatigue':    (8, 18),
            'total_reps':     (45, 90),
        },
    ],

    # =================================================================
    #  LABEL 2: HIGH EFFECTIVENESS  (4500 samples, 6 sub-profiles)
    # =================================================================
    2: [
        {
            # Solid session: 35-55 min of consistent, quality work.
            # Good bodyweight circuit or well-structured gym session.
            'name': 'solid_session',
            'count': 825,
            'duration_mins':  (35, 55),
            'avg_hr':         (125, 155),
            'max_hr_delta':   (15, 32),
            'hr_spikes':      (3, 7),
            'pct_time_low':   (4, 20),
            'avg_emg':        (360, 570),
            'emg_fatigue':    (15, 28),
            'total_reps':     (80, 160),
        },
        {
            # Intense shorter: 28-42 min where every minute is hard.
            # High HR, high EMG, not quite Maximum territory.
            'name': 'intense_shorter',
            'count': 750,
            'duration_mins':  (28, 42),
            'avg_hr':         (130, 158),
            'max_hr_delta':   (18, 35),
            'hr_spikes':      (4, 8),
            'pct_time_low':   (3, 15),
            'avg_emg':        (390, 570),
            'emg_fatigue':    (17, 30),
            'total_reps':     (80, 145),
        },
        {
            # Moderate-intensity but long: 45-65 min of sustained
            # moderate work. The effort x time product is still High.
            'name': 'moderate_long',
            'count': 750,
            'duration_mins':  (45, 65),
            'avg_hr':         (115, 142),
            'max_hr_delta':   (14, 28),
            'hr_spikes':      (2, 6),
            'pct_time_low':   (8, 28),
            'avg_emg':        (320, 500),
            'emg_fatigue':    (12, 24),
            'total_reps':     (70, 140),
        },
        {
            # Progressive overload: 38-55 min session that ramps up
            # in intensity. Moderate early EMG, higher late EMG.
            # Fatigue is significant because you pushed harder at the end.
            'name': 'progressive_overload',
            'count': 675,
            'duration_mins':  (38, 55),
            'avg_hr':         (120, 150),
            'max_hr_delta':   (15, 32),
            'hr_spikes':      (3, 7),
            'pct_time_low':   (5, 22),
            'avg_emg':        (340, 530),
            'emg_fatigue':    (14, 26),
            'total_reps':     (75, 145),
        },
        {
            # Superset style: 30-48 min with minimal rest between
            # exercises. HR stays elevated, good EMG throughout.
            'name': 'superset_style',
            'count': 750,
            'duration_mins':  (30, 48),
            'avg_hr':         (132, 158),
            'max_hr_delta':   (16, 32),
            'hr_spikes':      (3, 7),
            'pct_time_low':   (2, 14),
            'avg_emg':        (380, 560),
            'emg_fatigue':    (16, 28),
            'total_reps':     (90, 155),
        },
        {
            # Upper/lower split: focused compound lifts for 35-55 min.
            # Good structure, decent volume, solid effort.
            'name': 'compound_split',
            'count': 750,
            'duration_mins':  (35, 55),
            'avg_hr':         (118, 148),
            'max_hr_delta':   (14, 30),
            'hr_spikes':      (2, 6),
            'pct_time_low':   (6, 22),
            'avg_emg':        (350, 540),
            'emg_fatigue':    (14, 26),
            'total_reps':     (75, 150),
        },
    ],

    # =================================================================
    #  LABEL 3: MAXIMUM EFFECTIVENESS  (4500 samples, 8 sub-profiles)
    # =================================================================
    3: [
        {
            # Beast mode: everything near physiological ceiling.
            # Long session, extreme HR, extreme EMG, extreme volume.
            'name': 'beast_mode',
            'count': 750,
            'duration_mins':  (42, 72),
            'avg_hr':         (148, 178),
            'max_hr_delta':   (18, 38),
            'hr_spikes':      (6, 15),
            'pct_time_low':   (0, 5),
            'avg_emg':        (580, 820),
            'emg_fatigue':    (28, 52),
            'total_reps':     (150, 270),
        },
        {
            # One Rep Max testing: taking huge rests, doing a couple of massive singles.
            'name': 'one_rep_max_testing',
            'count': 600,
            'duration_mins':  (40, 90),
            'avg_hr':         (90, 115),
            'max_hr_delta':   (25, 45),
            'hr_spikes':      (2, 6),
            'pct_time_low':   (40, 75),
            'avg_emg':        (700, 950),
            'emg_fatigue':    (10, 30),
            'total_reps':     (3, 12),
        },
        {
            # Heavy powerlifting: low HR (3-5 min rests) but extreme
            # muscle engagement. Deadlifts, squats, bench at near-max.
            'name': 'powerlifting',
            'count': 600,
            'duration_mins':  (35, 62),
            'avg_hr':         (78, 105),
            'max_hr_delta':   (15, 38),
            'hr_spikes':      (1, 5),
            'pct_time_low':   (48, 80),
            'avg_emg':        (530, 740),
            'emg_fatigue':    (20, 42),
            'total_reps':     (5, 25),
        },
        {
            # High-rep endurance: lighter weight, extreme volume.
            # The sustained muscular effort makes this Maximum.
            'name': 'endurance_volume',
            'count': 600,
            'duration_mins':  (33, 58),
            'avg_hr':         (130, 165),
            'max_hr_delta':   (15, 30),
            'hr_spikes':      (3, 8),
            'pct_time_low':   (2, 18),
            'avg_emg':        (300, 480),
            'emg_fatigue':    (10, 24),
            'total_reps':     (180, 320),
        },
        {
            # Intense circuit: supersets and giant sets with minimal
            # rest. Everything elevated throughout.
            'name': 'intense_circuit',
            'count': 525,
            'duration_mins':  (32, 52),
            'avg_hr':         (140, 172),
            'max_hr_delta':   (18, 35),
            'hr_spikes':      (5, 13),
            'pct_time_low':   (0, 8),
            'avg_emg':        (510, 710),
            'emg_fatigue':    (24, 40),
            'total_reps':     (120, 225),
        },
        {
            # Drop sets to failure: 35-55 min where multiple sets go
            # to absolute muscular failure. Extreme fatigue signature.
            'name': 'drop_sets_failure',
            'count': 450,
            'duration_mins':  (35, 55),
            'avg_hr':         (135, 165),
            'max_hr_delta':   (18, 35),
            'hr_spikes':      (4, 10),
            'pct_time_low':   (2, 14),
            'avg_emg':        (480, 700),
            'emg_fatigue':    (30, 50),
            'total_reps':     (100, 200),
        },
        {
            # Full body destroyer: 45-68 min, high volume across all
            # major muscle groups. Both volume AND intensity are high.
            'name': 'full_body_destroyer',
            'count': 450,
            'duration_mins':  (45, 68),
            'avg_hr':         (142, 172),
            'max_hr_delta':   (18, 36),
            'hr_spikes':      (5, 12),
            'pct_time_low':   (0, 8),
            'avg_emg':        (550, 780),
            'emg_fatigue':    (26, 48),
            'total_reps':     (140, 250),
        },
        {
            # Competition-style training: structured, long (55-80 min),
            # high discipline, maximal effort throughout.
            'name': 'competition_training',
            'count': 525,
            'duration_mins':  (55, 80),
            'avg_hr':         (138, 168),
            'max_hr_delta':   (16, 35),
            'hr_spikes':      (5, 12),
            'pct_time_low':   (1, 10),
            'avg_emg':        (520, 750),
            'emg_fatigue':    (25, 45),
            'total_reps':     (160, 280),
        },
    ],
}


# =============================================================================
#  NAMED PROFILE REFERENCES  (for edge-case interpolation)
# =============================================================================
#  These are direct references into PROFILES so edge cases always stay in sync
#  with any future adjustments to the main profile ranges.

_P = {
    # Label 0
    'ultra_short_burst':  PROFILES[0][0],
    'medium_halfhearted': PROFILES[0][3],
    'distracted_gym':     PROFILES[0][5],
    # Label 1
    'light_recovery':     PROFILES[1][0],
    'average_session':    PROFILES[1][1],
    'short_decent':       PROFILES[1][3],
    'long_easy':          PROFILES[1][4],
    # Label 2
    'solid_session':      PROFILES[2][0],
    'intense_shorter':    PROFILES[2][1],
    # Label 3
    'beast_mode':         PROFILES[3][0],
    'powerlifting':       PROFILES[3][2],
    'endurance_volume':   PROFILES[3][3],
}

# Interpolation feature keys (must match profile dict keys exactly)
_FEAT_KEYS = [
    'duration_mins', 'avg_hr', 'max_hr_delta', 'hr_spikes',
    'pct_time_low', 'avg_emg', 'emg_fatigue', 'total_reps',
]


def interpolate_profiles(profile_a, profile_b, alpha_per_feature):
    """
    Create a pseudo-profile by linearly interpolating between two profiles.

    alpha_per_feature: dict {feature_key: float in [0, 1]}
        alpha = 1.0  => range fully from profile_a
        alpha = 0.0  => range fully from profile_b
        default 0.5  => midpoint between the two

    Returns a dict with the same keys as a normal profile, suitable for
    passing directly to generate_samples().
    """
    pseudo = {}
    for key in _FEAT_KEYS:
        alpha = alpha_per_feature.get(key, 0.5)
        lo = alpha * profile_a[key][0] + (1.0 - alpha) * profile_b[key][0]
        hi = alpha * profile_a[key][1] + (1.0 - alpha) * profile_b[key][1]
        pseudo[key] = (lo, hi)
    return pseudo


# =============================================================================
#  EDGE CASE DEFINITIONS  (8 interpolated profiles)
# =============================================================================
#
#  Each entry: {name, count, label, profile_a, profile_b, alpha_per_feature}
#
#  alpha_per_feature controls which features "lean" toward which profile.
#  HIGH-importance features (avg_emg, emg_fatigue, duration_mins, avg_hr)
#  are used to steer the predicted label; lower-importance features provide
#  ambiguity.
#
#  Labels confirmed by user (2026-06-01):
#     EC-01: 0 (Low)      EC-02: 2 (High — user override)
#     EC-03: 1 (Moderate) EC-04: 2 (High)
#     EC-05: 2 (High)     EC-06: 1 (Moderate)
#     EC-07: 1 (Moderate) EC-08: 0 (Low)

EDGE_CASES = [
    {
        # EC-01: Distracted gym behaviour with some light-recovery features.
        # 5 high-importance features lean Low (distracted_gym),
        # 3 secondary features lean Moderate (light_recovery).
        # Duration and EMG dominate → Low.
        'name':    'ec01_distracted_vs_recovery',
        'count':   300,
        'label':   0,
        'profile_a': _P['distracted_gym'],
        'profile_b': _P['light_recovery'],
        'alpha': {
            'avg_emg':      0.75,  # lean distracted (low EMG)
            'emg_fatigue':  0.75,  # lean distracted (low fatigue)
            'avg_hr':       0.75,  # lean distracted (low HR)
            'pct_time_low': 0.75,  # lean distracted (high pct_low)
            'duration_mins':0.75,  # lean distracted
            'hr_spikes':    0.25,  # lean light_recovery
            'total_reps':   0.25,  # lean light_recovery
            'max_hr_delta': 0.25,  # lean light_recovery
        },
    },
    {
        # EC-02: Mostly light-recovery features but the 3 most important
        # features (avg_emg, avg_hr, duration) lean into average_session
        # territory. User judged this as High (2).
        'name':    'ec02_recovery_vs_average',
        'count':   300,
        'label':   2,
        'profile_a': _P['light_recovery'],
        'profile_b': _P['average_session'],
        'alpha': {
            'avg_emg':      0.20,  # lean average_session (higher EMG)
            'avg_hr':       0.20,  # lean average_session (higher HR)
            'duration_mins':0.20,  # lean average_session (more duration)
            'emg_fatigue':  0.75,  # lean light_recovery (low fatigue)
            'pct_time_low': 0.75,  # lean light_recovery (more low-HR time)
            'hr_spikes':    0.75,  # lean light_recovery
            'total_reps':   0.75,  # lean light_recovery
            'max_hr_delta': 0.75,  # lean light_recovery
        },
    },
    {
        # EC-03: Short decent vs intense shorter — equally split.
        # Duration is the deciding factor: too short to be High.
        'name':    'ec03_short_decent_vs_intense',
        'count':   300,
        'label':   1,
        'profile_a': _P['short_decent'],
        'profile_b': _P['intense_shorter'],
        'alpha': {
            'duration_mins':0.70,  # lean short_decent (shorter)
            'emg_fatigue':  0.70,  # lean short_decent
            'avg_emg':      0.35,  # lean intense_shorter
            'avg_hr':       0.35,  # lean intense_shorter
            'hr_spikes':    0.35,  # lean intense_shorter
            'pct_time_low': 0.60,  # lean short_decent
            'total_reps':   0.50,  # midpoint
            'max_hr_delta': 0.50,  # midpoint
        },
    },
    {
        # EC-04: Average session vs solid session — evenly split but the
        # high-importance EMG/fatigue features edge toward High.
        'name':    'ec04_average_vs_solid',
        'count':   300,
        'label':   2,
        'profile_a': _P['average_session'],
        'profile_b': _P['solid_session'],
        'alpha': {
            'avg_emg':      0.35,  # lean solid_session
            'emg_fatigue':  0.35,  # lean solid_session
            'avg_hr':       0.35,  # lean solid_session
            'duration_mins':0.40,  # slight lean toward solid_session
            'hr_spikes':    0.40,  # slight lean toward solid_session
            'pct_time_low': 0.60,  # lean average_session
            'total_reps':   0.40,  # lean solid_session
            'max_hr_delta': 0.50,  # midpoint
        },
    },
    {
        # EC-05: Solid session vs beast mode — duration and volume from beast,
        # but intensity features stay High. Not quite Maximum.
        'name':    'ec05_solid_vs_beast',
        'count':   300,
        'label':   2,
        'profile_a': _P['solid_session'],
        'profile_b': _P['beast_mode'],
        'alpha': {
            'avg_emg':      0.65,  # lean solid_session
            'emg_fatigue':  0.60,  # lean solid_session
            'avg_hr':       0.65,  # lean solid_session
            'pct_time_low': 0.65,  # lean solid_session (not quite beast)
            'duration_mins':0.30,  # lean beast_mode (longer duration)
            'total_reps':   0.30,  # lean beast_mode (more reps)
            'hr_spikes':    0.50,  # midpoint
            'max_hr_delta': 0.50,  # midpoint
        },
    },
    {
        # EC-06: Powerlifting EMG meets halfhearted HR/reps.
        # Extreme avg_emg but everything else is weak → Moderate.
        'name':    'ec06_powerlifting_vs_halfhearted',
        'count':   300,
        'label':   1,
        'profile_a': _P['powerlifting'],
        'profile_b': _P['medium_halfhearted'],
        'alpha': {
            'avg_emg':      0.70,  # lean powerlifting (high EMG)
            'emg_fatigue':  0.70,  # lean powerlifting
            'avg_hr':       0.25,  # lean halfhearted (low HR)
            'pct_time_low': 0.25,  # lean halfhearted (lots of low-HR time)
            'total_reps':   0.25,  # lean halfhearted (low reps)
            'duration_mins':0.50,  # midpoint
            'hr_spikes':    0.25,  # lean halfhearted
            'max_hr_delta': 0.50,  # midpoint
        },
    },
    {
        # EC-07: Endurance volume reps but with long-easy EMG/HR.
        # High reps alone don't make Maximum; EMG is weak → Moderate.
        'name':    'ec07_endurance_vs_longeasy',
        'count':   300,
        'label':   1,
        'profile_a': _P['endurance_volume'],
        'profile_b': _P['long_easy'],
        'alpha': {
            'total_reps':   0.75,  # lean endurance_volume (huge reps)
            'duration_mins':0.60,  # lean endurance_volume
            'avg_emg':      0.25,  # lean long_easy (weak EMG)
            'emg_fatigue':  0.25,  # lean long_easy
            'avg_hr':       0.35,  # lean long_easy (lower HR)
            'pct_time_low': 0.35,  # lean long_easy
            'hr_spikes':    0.50,  # midpoint
            'max_hr_delta': 0.50,  # midpoint
        },
    },
    {
        # EC-08: Ultra-short burst vs short decent — mostly Low duration.
        # Duration is the decisive gating feature: sub-10 min → Low.
        'name':    'ec08_ultra_short_vs_decent',
        'count':   300,
        'label':   0,
        'profile_a': _P['ultra_short_burst'],
        'profile_b': _P['short_decent'],
        'alpha': {
            'duration_mins':0.65,  # lean ultra_short (short duration)
            'avg_hr':       0.35,  # lean short_decent (decent HR)
            'avg_emg':      0.35,  # lean short_decent (decent EMG)
            'emg_fatigue':  0.35,  # lean short_decent
            'hr_spikes':    0.50,  # midpoint
            'total_reps':   0.35,  # lean short_decent (more reps)
            'pct_time_low': 0.65,  # lean ultra_short
            'max_hr_delta': 0.50,  # midpoint
        },
    },
]



# =============================================================================
#  PHYSICAL CONSTRAINT ENFORCEMENT
# =============================================================================

def enforce_physical_constraints(sample):
    """
    Post-process a generated sample to guarantee physically consistent
    and realistic feature values.

    Rules:
        1. max_hr >= avg_hr  (always)
        2. max_hr <= 210     (physiological ceiling)
        3. pct_time_low inversely correlated with avg_hr
           (high avg_hr -> can't spend much time below 100 BPM)
           Exception: powerlifting (low avg_hr + high avg_emg) -> no clamp
        4. All features clamped to physically valid ranges
    """

    # ── Rule 1 & 2: max_hr ───────────────────────────────────────────────
    if sample['max_hr'] < sample['avg_hr']:
        sample['max_hr'] = sample['avg_hr'] + np.random.uniform(5, 15)
    sample['max_hr'] = min(sample['max_hr'], 210.0)

    # ── Rule 3: pct_time_low vs avg_hr consistency ───────────────────────
    # Only clamp for higher avg_hr (powerlifting has low avg_hr so these
    # clamps naturally don't fire for that archetype).
    if sample['avg_hr'] > 160:
        sample['pct_time_low'] = min(sample['pct_time_low'], 3.0)
    elif sample['avg_hr'] > 150:
        sample['pct_time_low'] = min(sample['pct_time_low'], 6.0)
    elif sample['avg_hr'] > 140:
        sample['pct_time_low'] = min(sample['pct_time_low'], 12.0)
    elif sample['avg_hr'] > 125:
        sample['pct_time_low'] = min(sample['pct_time_low'], 25.0)
    elif sample['avg_hr'] > 110:
        sample['pct_time_low'] = min(sample['pct_time_low'], 45.0)

    # ── Rule 4: hard clamps ──────────────────────────────────────────────
    sample['duration_mins'] = max(1.0,   sample['duration_mins'])
    sample['avg_hr']        = np.clip(sample['avg_hr'],        50, 200)
    sample['max_hr']        = np.clip(sample['max_hr'],        sample['avg_hr'], 210)
    sample['hr_spikes']     = max(0,     sample['hr_spikes'])
    sample['pct_time_low']  = np.clip(sample['pct_time_low'],  0, 100)
    sample['avg_emg']       = np.clip(sample['avg_emg'],       0, 1000)
    sample['emg_fatigue']   = np.clip(sample['emg_fatigue'],   0, 60)
    sample['total_reps']    = max(1,     sample['total_reps'])

    return sample


# =============================================================================
#  SAMPLE GENERATION
# =============================================================================

def generate_samples(n, profile, label):
    """
    Generate `n` samples from a sub-profile definition.
    """
    samples = []

    # Let's multiply n to scale up the dataset safely (e.g. 2.5x)
    n = int(n * 2.5)

    for _ in range(n):
        # 1. Generate Demographics
        age = np.random.randint(16, 66)
        weight_kg = round(np.random.uniform(50.0, 130.0), 1)
        fitness_level = np.random.choice(['low', 'medium', 'high'], p=[0.3, 0.5, 0.2])
        athlete_type = np.random.choice(['powerlifter', 'hybrid', 'gym_bro', 'non_athletic'], p=[0.1, 0.2, 0.5, 0.2])
        body_fat_pct = round(np.random.uniform(5.0, 35.0), 1)
        limb_length = np.random.choice(['short', 'medium', 'long'], p=[0.25, 0.5, 0.25])
        workout_type = np.random.choice(['HILV', 'LIHV', 'hypertrophy', 'endurance_lifting'], p=[0.2, 0.2, 0.4, 0.2])

        # 2. Base Profile Generation
        avg_hr = np.random.uniform(*profile['avg_hr'])
        max_hr_delta = np.random.uniform(*profile['max_hr_delta'])
        avg_emg = np.random.uniform(*profile['avg_emg'])
        emg_fatigue = np.random.uniform(*profile['emg_fatigue'])
        total_reps = int(np.random.uniform(*profile['total_reps']))
        hr_spikes = int(np.random.randint(profile['hr_spikes'][0], profile['hr_spikes'][1] + 1))
        duration_mins = np.random.uniform(*profile['duration_mins'])

        # 3. Apply Physiological Modifiers based on user research

        # Workout Type Modifiers (CRITICAL)
        if workout_type == 'HILV':
            total_reps = max(1, int(total_reps * 0.25))  # Slash reps
            avg_emg *= 1.5                               # Boost EMG
            hr_spikes += 2                               # More rests
        elif workout_type == 'LIHV':
            total_reps = int(total_reps * 1.5)           # Increase reps
            avg_emg *= 0.7                               # Lower EMG
        elif workout_type == 'endurance_lifting':
            total_reps = int(total_reps * 2.0)           # Massive reps
            avg_emg *= 0.6                               # Very low peak EMG
            avg_hr *= 1.25                               # Huge HR penalty
            emg_fatigue *= 0.7                           # Slow-twitch fibers don't fatigue fast

        # Neuromuscular Efficiency & Stroke Volume (Boosted to 20-30%)
        if fitness_level == 'high':
            avg_hr *= 0.80     # Lower HR for same work due to stroke volume
            avg_emg *= 1.25    # Better motor unit recruitment
        elif fitness_level == 'low':
            avg_hr *= 1.20
            avg_emg *= 0.75

        # Body Fat Penalty
        if body_fat_pct > 15.0:
            extra_fat = body_fat_pct - 15.0
            # +1% HR for every 2% body fat over 15%
            avg_hr *= (1 + (extra_fat / 200.0))

        # Leverages (Limb Length)
        if limb_length == 'long':
            emg_fatigue *= 1.15  # More mechanical work
            total_reps = max(1, int(total_reps * 0.9))
        elif limb_length == 'short':
            emg_fatigue *= 0.85
            total_reps = int(total_reps * 1.1)

        # Athlete Type Context
        if athlete_type == 'powerlifter':
            hr_spikes = max(0, hr_spikes - 2) # Taking longer rests = fewer spikes

        # Weight modifier — heavier body mass raises cardiovascular load
        # and produces higher absolute EMG (more muscle mass to activate).
        # Reference: 80 kg is a neutral baseline.
        weight_hr_factor  = 1.0 + (weight_kg - 80.0) / 500.0   # ±10% over 50 kg range
        weight_emg_factor = 1.0 + (weight_kg - 80.0) / 400.0   # ±12.5% over 50 kg range
        avg_hr  *= weight_hr_factor
        avg_emg *= weight_emg_factor

        # 4. Construct Sample
        sample = {
            'workout_id':          f"w_{uuid.uuid4().hex[:8]}",
            'age':                 age,
            'weight_kg':           weight_kg,
            'fitness_level':       fitness_level,
            'workout_type':        workout_type,
            'athlete_type':        athlete_type,
            'body_fat_pct':        body_fat_pct,
            'limb_length':         limb_length,
            'duration_mins':       duration_mins,
            'avg_hr':              avg_hr,
            'max_hr':              avg_hr + max_hr_delta,
            'hr_spikes':           hr_spikes,
            'pct_time_low':        np.random.uniform(*profile['pct_time_low']),
            'avg_emg':             avg_emg,
            'emg_fatigue':         emg_fatigue,
            'total_reps':          total_reps,
            'effectiveness_label': label,
        }

        # Apply physical constraints
        sample = enforce_physical_constraints(sample)

        # Enforce Age-based Max HR
        age_cap = 220 - age
        sample['max_hr'] = min(sample['max_hr'], age_cap)
        # Ensure avg_hr doesn't exceed the new capped max_hr
        sample['avg_hr'] = min(sample['avg_hr'], sample['max_hr'] - 2)

        # Round for cleanliness
        sample['duration_mins'] = round(sample['duration_mins'], 1)
        sample['avg_hr']        = round(sample['avg_hr'], 1)
        sample['max_hr']        = round(sample['max_hr'], 1)
        sample['pct_time_low']  = round(sample['pct_time_low'], 1)
        sample['avg_emg']       = round(sample['avg_emg'], 1)
        sample['emg_fatigue']   = round(sample['emg_fatigue'], 1)

        samples.append(sample)

    return samples


# =============================================================================
#  DATASET ASSEMBLY
# =============================================================================

def generate_dataset():
    """Generate the full balanced synthetic dataset from all profiles."""
    all_samples = []
    label_names = {0: 'LOW', 1: 'MODERATE', 2: 'HIGH', 3: 'MAXIMUM'}

    print("  Generating samples per sub-profile:\n")

    for label in sorted(PROFILES.keys()):
        sub_profiles = PROFILES[label]
        print(f"  +-- Label {label} ({label_names[label]}) --------------------")

        label_count = 0
        for profile in sub_profiles:
            samples = generate_samples(profile['count'], profile, label)
            all_samples.extend(samples)
            label_count += profile['count']
            print(f"  |   {profile['name']:28s} ->  {profile['count']:4d} samples")

        print(f'  +-- Subtotal: {label_count} samples\n')

    # ── Edge Cases ────────────────────────────────────────────────────────
    print('  +-- EDGE CASES (interpolated profiles) ------------------')
    ec_total = 0
    for ec in EDGE_CASES:
        pseudo = interpolate_profiles(ec['profile_a'], ec['profile_b'], ec['alpha'])
        ec_samples = generate_samples(ec['count'], pseudo, ec['label'])
        all_samples.extend(ec_samples)
        ec_total += ec['count']
        print(f"  |   {ec['name']:28s} ->  {ec['count']:4d} samples  (label={ec['label']})")
    print(f'  +-- Edge case subtotal: {ec_total} samples\n')


    # Shuffle the entire dataset
    np.random.shuffle(all_samples)

    # Build DataFrame with correct column order
    df = pd.DataFrame(all_samples)
    col_order = [
        'workout_id', 'age', 'weight_kg', 'fitness_level', 'workout_type', 'athlete_type', 'body_fat_pct', 'limb_length',
        'duration_mins', 'avg_hr', 'max_hr', 'hr_spikes',
        'pct_time_low', 'avg_emg', 'emg_fatigue', 'total_reps',
        'effectiveness_label'
    ]
    df = df[col_order]

    return df



# =============================================================================
#  ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print()
    print("=" * 62)
    print("   SYNTHETIC GYM WORKOUT DATA GENERATOR  v3")
    print("=" * 62)
    print()

    df = generate_dataset()

    # ── Save ─────────────────────────────────────────────────────────────
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"  Dataset saved to: {OUTPUT_PATH}")
    print(f"  Total samples:    {len(df)}")
    print()

    # ── Class distribution ───────────────────────────────────────────────
    label_names = {0: 'Low', 1: 'Moderate', 2: 'High', 3: 'Maximum'}
    print("  Class distribution:")
    for label in sorted(df['effectiveness_label'].unique()):
        count = len(df[df['effectiveness_label'] == label])
        print(f"      {label} ({label_names[label]:>8s}):  {count} samples")

    # ── Feature statistics ───────────────────────────────────────────────
    print()
    print("=" * 62)
    print("   FEATURE STATISTICS (excluding workout_id)")
    print("=" * 62)
    CATEGORICAL = {'workout_id', 'fitness_level', 'workout_type', 'athlete_type', 'limb_length', 'effectiveness_label'}
    numeric_cols = [c for c in df.columns if c not in CATEGORICAL]
    print(df[numeric_cols].describe().round(2).to_string())

    # ── Quick per-class means ────────────────────────────────────────────
    print()
    print("=" * 62)
    print("   PER-CLASS FEATURE MEANS")
    print("=" * 62)
    means = df.groupby('effectiveness_label')[numeric_cols].mean().round(1)

    means.index = [f"{i} ({label_names[i]})" for i in means.index]
    print(means.to_string())
    print()
