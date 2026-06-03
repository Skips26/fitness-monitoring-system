import { useEffect, useState } from 'react';
import { profileApi } from '../lib/api';
import DemographicForm from '../components/DemographicForm';

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await profileApi.get();
      setProfile(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (data) => {
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const updated = await profileApi.update(data);
      setProfile(updated);
      setSuccess('Profile updated successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-spinner"><div className="spinner" /></div>
      </div>
    );
  }

  return (
    <div className="page-container" style={{ maxWidth: '600px' }}>
      <div className="page-header animate-in">
        <h1>Profile</h1>
        <p>Update your demographic data for accurate AI analysis</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="card animate-in animate-in-delay-1">
        <div className="alert alert-info" style={{ marginBottom: 'var(--space-lg)' }}>
          Changes to your profile will affect future workout analyses.
          Previously analyzed workouts will keep their original results.
        </div>

        {profile && (
          <DemographicForm
            initialData={profile}
            onSubmit={handleUpdate}
            submitLabel="Update Profile"
            loading={saving}
          />
        )}
      </div>
    </div>
  );
}
