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

// ── Sensor field metadata for editing + anomaly detection ───────────────────
const SENSOR_FIELDS = [
  {
    key: 'duration_mins',
    label: 'Duration',
    unit: 'min',
    icon: '⏱️',
    step: 0.1,
    min: 0.1,
    anomaly: (v) => v < 1 || v > 180,
    anomalyMsg: 'Duration seems unusual',
    defaults: [
      { label: '30 min (short)', value: 30 },
      { label: '45 min (standard)', value: 45 },
      { label: '60 min (long)', value: 60 },
    ],
  },
  {
    key: 'avg_hr',
    label: 'Avg HR',
    unit: 'BPM',
    icon: '❤️',
    step: 0.1,
    min: 0,
    anomaly: (v) => v < 40 || v > 220,
    anomalyMsg: 'Heart rate looks incorrect',
    defaults: [
      { label: '75 BPM (resting)', value: 75 },
      { label: '120 BPM (moderate)', value: 120 },
      { label: '145 BPM (intense)', value: 145 },
    ],
  },
  {
    key: 'max_hr',
    label: 'Max HR',
    unit: 'BPM',
    icon: '💗',
    step: 0.1,
    min: 0,
    anomaly: (v) => v < 50 || v > 230,
    anomalyMsg: 'Max heart rate looks incorrect',
    defaults: [
      { label: '140 BPM (moderate)', value: 140 },
      { label: '165 BPM (intense)', value: 165 },
      { label: '185 BPM (max effort)', value: 185 },
    ],
  },
  {
    key: 'hr_spikes',
    label: 'HR Spikes',
    unit: '',
    icon: '📈',
    step: 1,
    min: 0,
    anomaly: (v) => v > 50,
    anomalyMsg: 'Spike count seems very high',
    defaults: [
      { label: '2 (few)', value: 2 },
      { label: '5 (moderate)', value: 5 },
      { label: '10 (many)', value: 10 },
    ],
  },
  {
    key: 'pct_time_low',
    label: 'Low Zone',
    unit: '%',
    icon: '😴',
    step: 0.1,
    min: 0,
    anomaly: () => false, // pct is always valid 0-100
    defaults: [],
  },
  {
    key: 'avg_emg',
    label: 'Avg EMG',
    unit: '',
    icon: '💪',
    step: 0.1,
    min: 0,
    anomaly: (v) => v > 1000,
    anomalyMsg: 'EMG value exceeds sensor range',
    defaults: [
      { label: '200 (light)', value: 200 },
      { label: '400 (moderate)', value: 400 },
      { label: '650 (intense)', value: 650 },
    ],
  },
  {
    key: 'emg_fatigue',
    label: 'Fatigue',
    unit: '%',
    icon: '🔥',
    step: 0.1,
    min: 0,
    anomaly: (v) => v > 60,
    anomalyMsg: 'Fatigue index exceeds maximum',
    defaults: [
      { label: '10% (low)', value: 10 },
      { label: '20% (moderate)', value: 20 },
      { label: '35% (high)', value: 35 },
    ],
  },
  {
    key: 'total_reps',
    label: 'Total Reps',
    unit: '',
    icon: '🔄',
    step: 1,
    min: 0,
    anomaly: (v) => v === 0,
    anomalyMsg: 'No reps detected — enter manually',
    defaults: [
      { label: '30 reps (light)', value: 30 },
      { label: '60 reps (moderate)', value: 60 },
      { label: '100 reps (heavy)', value: 100 },
    ],
  },
];

export default function WorkoutDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [workout, setWorkout] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedType, setSelectedType] = useState('');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Editable sensor data state
  const [editingField, setEditingField] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [savingField, setSavingField] = useState(false);
  const [showDefaultsFor, setShowDefaultsFor] = useState(null);

  // Track which fields have been modified by the user
  const [modifiedFields, setModifiedFields] = useState(new Set());

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
    setError('');
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

  // ── Inline editing handlers ───────────────────────────────────────────────

  const startEditing = (fieldKey) => {
    setEditingField(fieldKey);
    setEditValue(String(workout[fieldKey]));
    setShowDefaultsFor(null);
    setSuccessMsg('');
  };

  const cancelEditing = () => {
    setEditingField(null);
    setEditValue('');
  };

  const saveFieldValue = async (fieldKey, value) => {
    const numValue = Number(value);
    if (isNaN(numValue) || numValue < 0) return;

    setSavingField(true);
    setError('');
    try {
      const updated = await workoutsApi.updateData(id, { [fieldKey]: numValue });
      setWorkout(updated);
      setModifiedFields((prev) => new Set([...prev, fieldKey]));
      setEditingField(null);
      setEditValue('');
      setShowDefaultsFor(null);
      setSuccessMsg(`${SENSOR_FIELDS.find(f => f.key === fieldKey)?.label || fieldKey} updated`);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingField(false);
    }
  };

  const applyDefault = (fieldKey, value) => {
    saveFieldValue(fieldKey, value);
  };

  const toggleDefaults = (fieldKey) => {
    setShowDefaultsFor(showDefaultsFor === fieldKey ? null : fieldKey);
    setEditingField(null);
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
  const isPending = workout.status === 'pending';
  const needsType = !workout.workout_type;
  const readyToAnalyze = workout.workout_type && !isAnalyzed;

  // Determine current step for the pending flow
  const currentStep = isAnalyzed ? 4 : !isPending ? 0 : needsType ? 2 : 3;

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
      {successMsg && <div className="alert alert-success">{successMsg}</div>}

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

      {/* ── Step Indicator (for pending workouts) ─────────────────────────── */}
      {isPending && (
        <div className="step-indicator animate-in animate-in-delay-1">
          <div className={`step-item ${currentStep >= 1 ? 'active' : ''} ${currentStep > 1 ? 'done' : ''}`}>
            <div className="step-number">1</div>
            <div className="step-text">Review Data</div>
          </div>
          <div className="step-connector" />
          <div className={`step-item ${currentStep >= 2 ? 'active' : ''} ${currentStep > 2 ? 'done' : ''}`}>
            <div className="step-number">2</div>
            <div className="step-text">Workout Type</div>
          </div>
          <div className="step-connector" />
          <div className={`step-item ${currentStep >= 3 ? 'active' : ''}`}>
            <div className="step-number">3</div>
            <div className="step-text">AI Analysis</div>
          </div>
        </div>
      )}

      {/* ── Step 1: Editable Sensor Data ─────────────────────────────────── */}
      <div className="card mt-xl animate-in animate-in-delay-1">
        <div className="section-header" style={{ marginBottom: 'var(--space-lg)' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isPending ? '📝 Step 1: Review & Edit Sensor Data' : '📊 Sensor Data'}
          </h3>
          {isPending && (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Click any value to edit · Warnings shown for suspicious readings
            </span>
          )}
        </div>

        <div className="stats-grid">
          {SENSOR_FIELDS.map((field) => {
            const value = workout[field.key];
            const hasAnomaly = field.anomaly(value);
            const isEditing = editingField === field.key;
            const isModified = modifiedFields.has(field.key);
            const showingDefaults = showDefaultsFor === field.key;

            return (
              <div
                key={field.key}
                className={`stat-card editable-stat ${hasAnomaly && isPending ? 'anomaly' : ''} ${isModified ? 'modified' : ''} ${isEditing ? 'editing' : ''}`}
                id={`stat-${field.key}`}
              >
                {/* Anomaly warning badge */}
                {hasAnomaly && isPending && !isModified && (
                  <div className="anomaly-badge" title={field.anomalyMsg}>⚠️</div>
                )}

                {/* Modified indicator */}
                {isModified && (
                  <div className="modified-badge" title="Value was corrected">✓</div>
                )}

                <div className="stat-icon">{field.icon}</div>

                {isEditing ? (
                  /* ── Inline edit mode ──────────────────────────── */
                  <div className="stat-edit-form">
                    <input
                      type="number"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') saveFieldValue(field.key, editValue);
                        if (e.key === 'Escape') cancelEditing();
                      }}
                      step={field.step}
                      min={field.min}
                      className="stat-edit-input"
                      autoFocus
                      disabled={savingField}
                    />
                    <div className="stat-edit-actions">
                      <button
                        className="stat-edit-btn save"
                        onClick={() => saveFieldValue(field.key, editValue)}
                        disabled={savingField}
                        title="Save"
                      >
                        ✓
                      </button>
                      <button
                        className="stat-edit-btn cancel"
                        onClick={cancelEditing}
                        disabled={savingField}
                        title="Cancel"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ) : (
                  /* ── Display mode ──────────────────────────────── */
                  <>
                    <div
                      className={`stat-value ${isPending ? 'clickable' : ''}`}
                      onClick={() => isPending && startEditing(field.key)}
                      title={isPending ? 'Click to edit' : undefined}
                    >
                      {value}
                      {field.unit && <span className="stat-unit">{field.unit}</span>}
                      {isPending && <span className="edit-icon">✎</span>}
                    </div>
                  </>
                )}

                <div className="stat-label">{field.label}</div>

                {/* Default values dropdown */}
                {hasAnomaly && isPending && field.defaults.length > 0 && !isModified && (
                  <div className="defaults-section">
                    <button
                      className="btn-defaults-toggle"
                      onClick={() => toggleDefaults(field.key)}
                    >
                      {showingDefaults ? 'Hide defaults ▴' : 'Use default ▾'}
                    </button>

                    {showingDefaults && (
                      <div className="defaults-dropdown">
                        {field.defaults.map((d) => (
                          <button
                            key={d.value}
                            className="default-option"
                            onClick={() => applyDefault(field.key, d.value)}
                            disabled={savingField}
                          >
                            {d.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Show defaults button even for non-anomaly fields that ARE pending and have defaults */}
                {!hasAnomaly && isPending && field.defaults.length > 0 && (
                  <div className="defaults-section">
                    <button
                      className="btn-defaults-toggle subtle"
                      onClick={() => toggleDefaults(field.key)}
                    >
                      {showingDefaults ? 'Hide ▴' : 'Defaults ▾'}
                    </button>

                    {showingDefaults && (
                      <div className="defaults-dropdown">
                        {field.defaults.map((d) => (
                          <button
                            key={d.value}
                            className="default-option"
                            onClick={() => applyDefault(field.key, d.value)}
                            disabled={savingField}
                          >
                            {d.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Anomaly summary */}
        {isPending && SENSOR_FIELDS.some((f) => f.anomaly(workout[f.key]) && !modifiedFields.has(f.key)) && (
          <div className="anomaly-summary mt-lg">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <span>
              Some sensor readings look unusual. Click a value to edit it, or use the &quot;Use default&quot; button to apply a standard value.
            </span>
          </div>
        )}
      </div>

      {/* ── Step 2: Workout Type Selection (if pending) ──────────────────── */}
      {isPending && (
        <div className="card mt-xl animate-in animate-in-delay-2">
          <h3 style={{ marginBottom: 'var(--space-md)' }}>
            {needsType ? '🎯 Step 2: Select Workout Type' : '✅ Workout Type Selected'}
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

      {/* ── Step 3: Analyze Button ───────────────────────────────────────── */}
      {readyToAnalyze && (
        <div className="card mt-xl text-center animate-in animate-in-delay-2">
          <h3 style={{ marginBottom: 'var(--space-md)' }}>
            🤖 Step 3: Run AI Analysis
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

      {/* ── AI Results ───────────────────────────────────────────────────── */}
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

          {/* Workout type info */}
          <div className="card mt-xl animate-in animate-in-delay-4">
            <h3 style={{ marginBottom: 'var(--space-md)' }}>Workout Configuration</h3>
            <div style={{ display: 'flex', gap: 'var(--space-xl)', flexWrap: 'wrap' }}>
              <div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Type</span>
                <div style={{ fontWeight: 600, marginTop: '4px', fontSize: '1.1rem' }}>
                  {TYPE_OPTIONS.find(t => t.value === workout.workout_type)?.icon}{' '}
                  {TYPE_OPTIONS.find(t => t.value === workout.workout_type)?.name || workout.workout_type}
                </div>
              </div>
              <div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Confidence</span>
                <div style={{ fontWeight: 600, marginTop: '4px', fontSize: '1.1rem' }}>
                  {Math.round(workout.confidence * 100)}%
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
