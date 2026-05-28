import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { workoutsApi } from '../lib/api';
import WorkoutCard from '../components/WorkoutCard';
import EffectivenessGauge from '../components/EffectivenessGauge';

export default function Dashboard() {
  const [workouts, setWorkouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadWorkouts();
  }, []);

  const loadWorkouts = async () => {
    try {
      const data = await workoutsApi.list();
      setWorkouts(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const latestAnalyzed = workouts.find((w) => w.status === 'analyzed');
  const pendingCount = workouts.filter((w) => w.status === 'pending').length;

  // Stats
  const analyzedWorkouts = workouts.filter((w) => w.status === 'analyzed');
  const totalWorkouts = workouts.length;
  const avgConfidence = analyzedWorkouts.length > 0
    ? (analyzedWorkouts.reduce((sum, w) => sum + w.confidence, 0) / analyzedWorkouts.length)
    : 0;
  const effectivenessDistribution = analyzedWorkouts.reduce((acc, w) => {
    acc[w.effectiveness_name] = (acc[w.effectiveness_name] || 0) + 1;
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-spinner"><div className="spinner" /></div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header animate-in">
        <h1>Dashboard</h1>
        <p>Your workout performance at a glance</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Stats Overview */}
      <div className="stats-grid animate-in animate-in-delay-1">
        <div className="stat-card">
          <div className="stat-icon">🏋️</div>
          <div className="stat-value">{totalWorkouts}</div>
          <div className="stat-label">Total Workouts</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-value">{analyzedWorkouts.length}</div>
          <div className="stat-label">Analyzed</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⏳</div>
          <div className="stat-value">{pendingCount}</div>
          <div className="stat-label">Pending</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🎯</div>
          <div className="stat-value">{avgConfidence > 0 ? `${Math.round(avgConfidence * 100)}%` : '—'}</div>
          <div className="stat-label">Avg Confidence</div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="dashboard-grid mt-xl">
        {/* Latest Result */}
        <div className="card animate-in animate-in-delay-2">
          <h3 style={{ marginBottom: 'var(--space-lg)' }}>Latest Result</h3>
          {latestAnalyzed ? (
            <div className="text-center">
              <EffectivenessGauge
                label={latestAnalyzed.effectiveness_name}
                confidence={latestAnalyzed.confidence}
              />
              <p style={{
                color: 'var(--text-secondary)',
                fontSize: '0.85rem',
                marginTop: 'var(--space-md)',
                maxWidth: '300px',
                margin: 'var(--space-md) auto 0',
              }}>
                {latestAnalyzed.explanation}
              </p>
              <Link
                to={`/workout/${latestAnalyzed.id}`}
                className="btn btn-secondary mt-lg"
              >
                View Details →
              </Link>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📊</div>
              <p>No analyzed workouts yet</p>
              <p style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                Complete a workout with the belt to see results here
              </p>
            </div>
          )}
        </div>

        {/* Effectiveness Distribution */}
        <div className="card animate-in animate-in-delay-3">
          <h3 style={{ marginBottom: 'var(--space-lg)' }}>Effectiveness Breakdown</h3>
          {analyzedWorkouts.length > 0 ? (
            <div className="prob-bars">
              {['Maximum', 'High', 'Moderate', 'Low'].map((level) => {
                const count = effectivenessDistribution[level] || 0;
                const pct = analyzedWorkouts.length > 0 ? (count / analyzedWorkouts.length) * 100 : 0;
                const colorVar = `var(--eff-${level.toLowerCase()})`;

                return (
                  <div className="prob-bar-row" key={level}>
                    <span className="prob-bar-label" style={{ color: colorVar }}>{level}</span>
                    <div className="prob-bar-track">
                      <div
                        className="prob-bar-fill"
                        style={{ width: `${pct}%`, background: colorVar }}
                      />
                    </div>
                    <span className="prob-bar-value">{count}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📈</div>
              <p>Data will appear after your first analyzed workout</p>
            </div>
          )}
        </div>
      </div>

      {/* Workout History */}
      <div className="animate-in animate-in-delay-4 mt-xl">
        <div className="section-header">
          <h2>Workout History</h2>
          {pendingCount > 0 && (
            <span className="badge badge-pending">{pendingCount} pending</span>
          )}
        </div>

        {workouts.length > 0 ? (
          <div className="workout-list">
            {workouts.map((workout) => (
              <WorkoutCard key={workout.id} workout={workout} />
            ))}
          </div>
        ) : (
          <div className="card">
            <div className="empty-state">
              <div className="empty-state-icon">🏋️</div>
              <h3>No workouts yet</h3>
              <p style={{ marginTop: 'var(--space-sm)' }}>
                Start a workout session with the fitness belt. Once you stop,
                the sensor data will appear here automatically.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
