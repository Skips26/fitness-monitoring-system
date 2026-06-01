import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function ManualWorkoutForm({ onSubmit, onCancel, loading }) {
  const { user } = useAuth();
  const [formData, setFormData] = useState({
    duration_mins: 45,
    avg_hr: 130,
    max_hr: 160,
    hr_spikes: 3,
    pct_time_low: 15.0,
    avg_emg: 450,
    emg_fatigue: 18.0,
    total_reps: 100,
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Ensure all numeric strings are parsed to floats/ints
    const payload = {
      user_id: user.id, // Required by the /workouts POST endpoint
      duration_mins: parseFloat(formData.duration_mins),
      avg_hr: parseFloat(formData.avg_hr),
      max_hr: parseFloat(formData.max_hr),
      hr_spikes: parseInt(formData.hr_spikes),
      pct_time_low: parseFloat(formData.pct_time_low),
      avg_emg: parseFloat(formData.avg_emg),
      emg_fatigue: parseFloat(formData.emg_fatigue),
      total_reps: parseInt(formData.total_reps),
    };
    onSubmit(payload);
  };

  return (
    <div className="card animate-in">
      <div className="section-header">
        <h3>Simulate Hardware Data</h3>
        <button className="btn btn-ghost" onClick={onCancel} disabled={loading}>
          Close
        </button>
      </div>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
        Manually inject sensor data to simulate a workout completed with the Raspberry Pi.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Duration (mins)</label>
            <input className="form-input" type="number" name="duration_mins" value={formData.duration_mins} onChange={handleChange} step="0.1" required />
          </div>
          <div className="form-group">
            <label className="form-label">Total Reps</label>
            <input className="form-input" type="number" name="total_reps" value={formData.total_reps} onChange={handleChange} required />
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Avg HR (BPM)</label>
            <input className="form-input" type="number" name="avg_hr" value={formData.avg_hr} onChange={handleChange} step="0.1" required />
          </div>
          <div className="form-group">
            <label className="form-label">Max HR (BPM)</label>
            <input className="form-input" type="number" name="max_hr" value={formData.max_hr} onChange={handleChange} step="0.1" required />
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">HR Spikes</label>
            <input className="form-input" type="number" name="hr_spikes" value={formData.hr_spikes} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label className="form-label">Time in Low HR (%)</label>
            <input className="form-input" type="number" name="pct_time_low" value={formData.pct_time_low} onChange={handleChange} step="0.1" required />
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Avg EMG (0-1000)</label>
            <input className="form-input" type="number" name="avg_emg" value={formData.avg_emg} onChange={handleChange} step="0.1" required />
          </div>
          <div className="form-group">
            <label className="form-label">EMG Fatigue (%)</label>
            <input className="form-input" type="number" name="emg_fatigue" value={formData.emg_fatigue} onChange={handleChange} step="0.1" required />
          </div>
        </div>

        <button type="submit" className="btn btn-primary w-full mt-lg" disabled={loading}>
          {loading ? 'Submitting...' : 'Send Sensor Data'}
        </button>
      </form>
    </div>
  );
}
