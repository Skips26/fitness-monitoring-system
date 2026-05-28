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
