-- =============================================================================
--   FITNESS MONITORING SYSTEM — Supabase Database Schema
--   Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- =============================================================================

-- ── Profiles table ──────────────────────────────────────────────────────────
-- Linked to Supabase Auth users via the `id` column.
-- Stores the demographic features needed by the AI model.

CREATE TABLE IF NOT EXISTS profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),

    -- AI Model demographic features
    age             INTEGER NOT NULL,
    fitness_level   VARCHAR(10) NOT NULL CHECK (fitness_level IN ('low', 'medium', 'high')),
    athlete_type    VARCHAR(20) NOT NULL CHECK (athlete_type IN ('powerlifter', 'hybrid', 'gym_bro', 'non_athletic')),
    body_fat_pct    DECIMAL(4,1) NOT NULL CHECK (body_fat_pct >= 3.0 AND body_fat_pct <= 50.0),
    limb_length     VARCHAR(10) NOT NULL CHECK (limb_length IN ('short', 'medium', 'long')),

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Workouts table ──────────────────────────────────────────────────────────
-- Stores sensor data from the Raspberry Pi and AI prediction results.

CREATE TABLE IF NOT EXISTS workouts (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- User-selected on web app after sensor data arrives
    workout_type         VARCHAR(20) CHECK (workout_type IN ('HILV', 'LIHV', 'hypertrophy', 'endurance_lifting')),

    -- Raspberry Pi sensor features (8 features)
    duration_mins        DECIMAL(5,1) NOT NULL,
    avg_hr               DECIMAL(5,1) NOT NULL,
    max_hr               DECIMAL(5,1) NOT NULL,
    hr_spikes            INTEGER NOT NULL DEFAULT 0,
    pct_time_low         DECIMAL(5,1) NOT NULL DEFAULT 0,
    avg_emg              DECIMAL(6,1) NOT NULL DEFAULT 0,
    emg_fatigue          DECIMAL(5,1) NOT NULL DEFAULT 0,
    total_reps           INTEGER NOT NULL DEFAULT 0,

    -- AI prediction results (NULL until analysis is triggered)
    effectiveness_label  INTEGER,
    effectiveness_name   VARCHAR(10),
    confidence           DECIMAL(5,4),
    probabilities        JSONB,
    explanation          TEXT,
    top_factors          JSONB,

    -- Status tracking
    status               VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'analyzed')),
    recorded_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_workouts_user_id ON workouts(user_id);
CREATE INDEX IF NOT EXISTS idx_workouts_recorded_at ON workouts(recorded_at DESC);

-- ── Row Level Security ──────────────────────────────────────────────────────
-- Enable RLS but allow service role to bypass (our FastAPI backend uses service role)

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE workouts ENABLE ROW LEVEL SECURITY;

-- Profiles: users can read/update their own profile
CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Workouts: users can read their own workouts
CREATE POLICY "Users can view own workouts"
    ON workouts FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own workouts"
    ON workouts FOR INSERT
    WITH CHECK (true);  -- Pi sends data with user_id, no auth

CREATE POLICY "Users can update own workouts"
    ON workouts FOR UPDATE
    USING (auth.uid() = user_id);
