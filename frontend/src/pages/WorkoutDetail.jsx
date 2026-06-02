import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { workoutsApi } from '../lib/api';
import EffectivenessGauge from '../components/EffectivenessGauge';
import ShapExplanation from '../components/ShapExplanation';

const TYPE_OPTIONS = [
  { value: 'hypertrophy', icon: '🏋️', name: 'Hypertrophy', desc: 'Standard 8-12 rep bodybuilding' },
  { value: 'HILV', icon: '🔥', name: 'HILV', desc: 'High Intensity, Low Volume' },
  { value: 'LIHV', icon: '🔄', name: 'LIHV', desc: 'Low Intensity, High Volume' },
  { value: 'endurance_lifting', icon: '⚡', name: 'Endurance', desc: 'High rep endurance lifting' },
];

const LABEL_COLORS = {
  Low: 'var(--eff-low)',
  Moderate: 'var(--eff-moderate)',
  High: 'var(--eff-high)',
  Maximum: 'var(--eff-maximum)',
};

export default function WorkoutDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [workout, setWorkout] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedType, setSelectedType] = useState('');
  const [error, setError] = useState('');
  const [showRepsModal, setShowRepsModal] = useState(false);
  const [repsInput, setRepsInput] = useState('');
  const [savingReps, setSavingReps] = useState(false);

  useEffect(() => {
    loadWorkout();
  }, [id]);

  const loadWorkout = async () => {
    try {
      const data = await workoutsApi.get(id);
      setWorkout(data);
      if (data.workout_type) {
        setSelectedType(data.workout_type);
      }
      // Auto-show reps modal if workout is pending and reps weren't sensor-counted
      if (data.status === 'pending' && data.total_reps === 0) {
        setShowRepsModal(true);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSetType = async (type) => {
    setSelectedType(type);
    try {
      await workoutsApi.setType(id, type);
      setWorkout((prev) => ({ ...prev, workout_type: type }));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError('');
    try {
      const updated = await workoutsApi.analyze(id);
      setWorkout(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSaveReps = async () => {
    const reps = parseInt(repsInput, 10);
    if (isNaN(reps) || reps < 0) return;
    setSavingReps(true);
    try {
      const updated = await workoutsApi.updateReps(id, reps);
      setWorkout(updated);
      setShowRepsModal(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingReps(false);
    }
  };

  const handleSkipReps = () => {
    setShowRepsModal(false);
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-spinner"><div className="spinner" /></div>
      </div>
    );
  }

  if (!workout) {
    return (
      <div className="page-container">
        <div className="alert alert-error">Workout not found</div>
      </div>
    );
  }

  const isAnalyzed = workout.status === 'analyzed';
  const needsType = !workout.workout_type;
  const readyToAnalyze = workout.workout_type && !isAnalyzed;

  return (
    <div className="page-container">

      {/* ── Reps Modal ─────────────────────────────────────────────────── */}
      {showRepsModal && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          background: 'rgba(0,0,0,0.65)',
          backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '1rem',
        }}>
          <div style={{
            background: 'rgba(20, 27, 45, 0.95)',
            border: '1px solid rgba(99,102,241,0.35)',
            borderRadius: '1.25rem',
            padding: '2rem',
            width: '100%',
            maxWidth: '420px',
            boxShadow: '0 24px 60px rgba(0,0,0,0.5)',
          }}>
            <div style={{ fontSize: '2.5rem', textAlign: 'center', marginBottom: '0.75rem' }}>🔄</div>
            <h2 style={{ textAlign: 'center', marginBottom: '0.5rem', fontSize: '1.3rem' }}>
              How many reps did you do?
            </h2>
            <p style={{ color: 'var(--text-secondary)', textAlign: 'center', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
              The sensor couldn't count reps automatically.<br />
              Enter your total rep count for this session.
            </p>

            <input
              id="reps-input"
              type="number"
              min="0"
              placeholder="e.g. 48"
              value={repsInput}
              onChange={(e) => setRepsInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSaveReps()}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                fontSize: '1.25rem',
                textAlign: 'center',
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(99,102,241,0.4)',
                borderRadius: '0.75rem',
                color: 'var(--text-primary)',
                outline: 'none',
                marginBottom: '1.25rem',
                boxSizing: 'border-box',
              }}
              autoFocus
            />

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1 }}
                onClick={handleSkipReps}
                disabled={savingReps}
              >
                Skip
              </button>
              <button
                id="save-reps-btn"
                className="btn btn-primary"
                style={{ flex: 2 }}
                onClick={handleSaveReps}
                disabled={savingReps || repsInput === ''}
              >
                {savingReps ? 'Saving…' : 'Save Reps'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Back button */}
      <button
        className="btn btn-ghost mb-lg animate-in"
        onClick={() => navigate('/dashboard')}
      >
        ← Back to Dashboard
      </button>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Header */}
      <div className="page-header animate-in">
        <div className="flex items-center gap-md">
          <h1>Workout Details</h1>
          {isAnalyzed && (
            <span className={`badge badge-${workout.effectiveness_name?.toLowerCase()}`}>
              {workout.effectiveness_name}
            </span>
          )}
          {!isAnalyzed && <span className="badge badge-pending">Pending</span>}
        </div>
        <p>
          {new Date(workout.recorded_at).toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>

      {/* Sensor Data Stats */}
      <div className="stats-grid animate-in animate-in-delay-1">
        <div className="stat-card">
          <div className="stat-icon">⏱️</div>
          <div className="stat-value">{workout.duration_mins}</div>
          <div className="stat-label">Minutes</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">❤️</div>
          <div className="stat-value">{workout.avg_hr}</div>
          <div className="stat-label">Avg HR (BPM)</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💗</div>
          <div className="stat-value">{workout.max_hr}</div>
          <div className="stat-label">Max HR (BPM)</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📈</div>
          <div className="stat-value">{workout.hr_spikes}</div>
          <div className="stat-label">HR Spikes</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">😴</div>
          <div className="stat-value">{workout.pct_time_low}%</div>
          <div className="stat-label">Time in Low Zone</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💪</div>
          <div className="stat-value">{workout.avg_emg}</div>
          <div className="stat-label">Avg EMG</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🔥</div>
          <div className="stat-value">{workout.emg_fatigue}%</div>
          <div className="stat-label">Muscle Fatigue</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🔄</div>
          <div className="stat-value">{workout.total_reps}</div>
          <div className="stat-label">Total Reps</div>
        </div>
      </div>

      {/* Workout Type Selection (if pending) */}
      {needsType && (
        <div className="card mt-xl animate-in animate-in-delay-2">
          <h3 style={{ marginBottom: 'var(--space-md)' }}>
            Step 1: Select Workout Type
          </h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-lg)', fontSize: '0.9rem' }}>
            What type of resistance training was this session? This helps the AI
            understand that 5 heavy reps can be just as effective as 200 light reps.
          </p>

          <div className="workout-type-grid">
            {TYPE_OPTIONS.map((opt) => (
              <div
                key={opt.value}
                className={`type-option ${selectedType === opt.value ? 'selected' : ''}`}
                onClick={() => handleSetType(opt.value)}
              >
                <div className="type-option-icon">{opt.icon}</div>
                <div className="type-option-name">{opt.name}</div>
                <div className="type-option-desc">{opt.desc}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analyze Button */}
      {readyToAnalyze && (
        <div className="card mt-xl text-center animate-in animate-in-delay-2">
          <h3 style={{ marginBottom: 'var(--space-md)' }}>
            Step 2: Run AI Analysis
          </h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-lg)', fontSize: '0.9rem' }}>
            The AI will merge your demographic profile with the sensor data to predict
            workout effectiveness with a detailed explanation.
          </p>
          <button
            className="btn btn-primary btn-lg"
            onClick={handleAnalyze}
            disabled={analyzing}
          >
            {analyzing ? '🤖 Analyzing...' : '🤖 Analyze Workout'}
          </button>
        </div>
      )}

      {/* AI Results */}
      {isAnalyzed && (
        <>
          <div className="dashboard-grid mt-xl">
            {/* Gauge */}
            <div className="card animate-in animate-in-delay-2">
              <h3 style={{ marginBottom: 'var(--space-lg)' }}>Effectiveness Rating</h3>
              <EffectivenessGauge
                label={workout.effectiveness_name}
                confidence={workout.confidence}
                size={200}
              />
            </div>

            {/* Probability Distribution */}
            <div className="card animate-in animate-in-delay-3">
              <h3 style={{ marginBottom: 'var(--space-lg)' }}>Class Probabilities</h3>
              <div className="prob-bars" style={{ marginTop: 'var(--space-md)' }}>
                {workout.probabilities && ['Maximum', 'High', 'Moderate', 'Low'].map((level) => {
                  const prob = workout.probabilities[level] || 0;
                  const pct = prob * 100;
                  const color = LABEL_COLORS[level];
                  const isWinner = level === workout.effectiveness_name;

                  return (
                    <div className="prob-bar-row" key={level}>
                      <span
                        className="prob-bar-label"
                        style={{
                          color: isWinner ? color : 'var(--text-secondary)',
                          fontWeight: isWinner ? 700 : 400,
                        }}
                      >
                        {level}
                      </span>
                      <div className="prob-bar-track">
                        <div
                          className="prob-bar-fill"
                          style={{ width: `${pct}%`, background: color }}
                        />
                      </div>
                      <span
                        className="prob-bar-value"
                        style={{
                          color: isWinner ? color : undefined,
                          fontWeight: isWinner ? 700 : undefined,
                        }}
                      >
                        {pct.toFixed(1)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* SHAP Explanation */}
          <div className="card mt-xl animate-in animate-in-delay-4">
            <h3 style={{ marginBottom: 'var(--space-lg)' }}>
              🧠 AI Explanation — Why this rating?
            </h3>
            <ShapExplanation
              topFactors={workout.top_factors}
              explanation={workout.explanation}
            />
          </div>
        </>
      )}
    </div>
  );
}
