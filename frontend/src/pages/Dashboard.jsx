import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { workoutsApi } from '../lib/api';
import WorkoutCard from '../components/WorkoutCard';
import EffectivenessGauge from '../components/EffectivenessGauge';
import ManualWorkoutForm from '../components/ManualWorkoutForm';
import { motion } from 'framer-motion';

export default function Dashboard() {
  const [workouts, setWorkouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showManualForm, setShowManualForm] = useState(false);
  const [submittingManual, setSubmittingManual] = useState(false);

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

  const handleManualSubmit = async (payload) => {
    setSubmittingManual(true);
    setError('');
    try {
      await workoutsApi.create(payload);
      setShowManualForm(false);
      await loadWorkouts(); // reload list
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmittingManual(false);
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

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 16 },
    show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 80, damping: 20 } }
  };
  return (
    <div className="page-container">
      <div className="page-header animate-in">
        <h1>Dashboard</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Your workout performance at a glance</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Stats Overview */}
      <motion.div 
        className="stats-grid"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        <motion.div className="stat-card" variants={itemVariants}>
          <div className="stat-icon" style={{ color: 'var(--accent-primary)' }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
          </div>
          <div className="stat-value">{totalWorkouts}</div>
          <div className="stat-label">Total Workouts</div>
        </motion.div>

        <motion.div className="stat-card" variants={itemVariants}>
          <div className="stat-icon" style={{ color: 'var(--accent-success)' }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
          </div>
          <div className="stat-value">{analyzedWorkouts.length}</div>
          <div className="stat-label">Analyzed</div>
        </motion.div>

        <motion.div className="stat-card" variants={itemVariants}>
          <div className="stat-icon" style={{ color: 'var(--accent-warning)' }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          </div>
          <div className="stat-value">{pendingCount}</div>
          <div className="stat-label">Pending</div>
        </motion.div>

        <motion.div className="stat-card" variants={itemVariants}>
          <div className="stat-icon" style={{ color: 'var(--accent-secondary)' }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>
          </div>
          <div className="stat-value">{avgConfidence > 0 ? `${Math.round(avgConfidence * 100)}%` : '\u2014'}</div>
          <div className="stat-label">Avg Confidence</div>
        </motion.div>
      </motion.div>

      {/* Main Grid */}
      <motion.div 
        className="dashboard-grid mt-xl"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {/* Latest Result */}
        <motion.div className="card" variants={itemVariants}>
          <h3 style={{ marginBottom: 'var(--space-lg)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20v-6M6 20V10M18 20V4"></path></svg>
            Latest Result
          </h3>
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
                lineHeight: '1.6',
              }}>
                {latestAnalyzed.explanation}
              </p>
              <Link
                to={`/workout/${latestAnalyzed.id}`}
                className="btn btn-secondary mt-lg"
                style={{ display: 'inline-flex' }}
              >
                View Details
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
              </Link>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
              </div>
              <p>No analyzed workouts yet</p>
              <p style={{ fontSize: '0.82rem', marginTop: '4px', color: 'var(--text-muted)' }}>
                Complete a workout with the belt to see results here
              </p>
            </div>
          )}
        </motion.div>

        {/* Effectiveness Distribution */}
        <motion.div className="card" variants={itemVariants}>
          <h3 style={{ marginBottom: 'var(--space-lg)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-secondary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>
            Effectiveness Breakdown
          </h3>
          {analyzedWorkouts.length > 0 ? (
            <div className="prob-bars">
              {['Maximum', 'High', 'Moderate', 'Low'].map((level, i) => {
                const count = effectivenessDistribution[level] || 0;
                const pct = analyzedWorkouts.length > 0 ? (count / analyzedWorkouts.length) * 100 : 0;
                const colorVar = `var(--eff-${level.toLowerCase()})`;

                return (
                  <motion.div 
                    className="prob-bar-row" 
                    key={level}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4, delay: 0.2 + i * 0.08 }}
                  >
                    <span className="prob-bar-label" style={{ color: colorVar }}>{level}</span>
                    <div className="prob-bar-track">
                      <motion.div
                        className="prob-bar-fill"
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8, delay: 0.3 + i * 0.08, ease: 'easeOut' }}
                        style={{ background: colorVar }}
                      />
                    </div>
                    <span className="prob-bar-value">{count}</span>
                  </motion.div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
              </div>
              <p>Data will appear after your first analyzed workout</p>
            </div>
          )}
        </motion.div>
      </motion.div>

      {/* Workout History */}
      <motion.div 
        className="mt-xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <div className="section-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
            <h2>Workout History</h2>
            {pendingCount > 0 && (
              <span className="badge badge-pending">{pendingCount} pending</span>
            )}
          </div>
          <button 
            className="btn btn-secondary" 
            onClick={() => setShowManualForm(!showManualForm)}
          >
            {showManualForm ? 'Hide Form' : '+ Log Manual Workout'}
          </button>
        </div>

        {showManualForm && (
          <div style={{ marginBottom: 'var(--space-xl)' }}>
            <ManualWorkoutForm 
              onSubmit={handleManualSubmit} 
              onCancel={() => setShowManualForm(false)}
              loading={submittingManual}
            />
          </div>
        )}

        {workouts.length > 0 ? (
          <motion.div 
            className="workout-list"
            variants={containerVariants}
            initial="hidden"
            animate="show"
          >
            {workouts.map((workout) => (
              <motion.div key={workout.id} variants={itemVariants}>
                <WorkoutCard workout={workout} />
              </motion.div>
            ))}
          </motion.div>
        ) : (
          <div className="card">
            <div className="empty-state">
              <div className="empty-state-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8h1a4 4 0 0 1 0 8h-1"></path><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path><line x1="6" y1="1" x2="6" y2="4"></line><line x1="10" y1="1" x2="10" y2="4"></line><line x1="14" y1="1" x2="14" y2="4"></line></svg>
              </div>
              <h3 style={{ marginBottom: 'var(--space-sm)' }}>No workouts yet</h3>
              <p style={{ marginTop: 'var(--space-sm)', color: 'var(--text-muted)' }}>
                Start a workout session with the fitness belt. Once you stop,
                the sensor data will appear here automatically.
              </p>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
