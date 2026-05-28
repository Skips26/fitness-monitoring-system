import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { profileApi } from '../lib/api';
import DemographicForm from '../components/DemographicForm';

export default function Register() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1 = account, 2 = demographics
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAccountSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signUp(email, password);
      setStep(2);
    } catch (err) {
      setError(err.message || 'Failed to create account');
    } finally {
      setLoading(false);
    }
  };

  const handleDemographicSubmit = async (data) => {
    setError('');
    setLoading(true);

    try {
      await profileApi.create(data);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Failed to save profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="card auth-card animate-in">
        <div className="auth-title">
          <h1>{step === 1 ? 'Create Account' : 'Your Profile'}</h1>
          <p>
            {step === 1
              ? 'Start tracking your workout effectiveness'
              : 'Tell us about yourself for personalized AI analysis'}
          </p>

          {/* Step indicator */}
          <div className="flex justify-center gap-sm mt-md">
            <div
              style={{
                width: 32,
                height: 4,
                borderRadius: 2,
                background: 'var(--accent-primary)',
              }}
            />
            <div
              style={{
                width: 32,
                height: 4,
                borderRadius: 2,
                background: step === 2 ? 'var(--accent-primary)' : 'var(--border-subtle)',
                transition: 'background 0.3s',
              }}
            />
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {step === 1 && (
          <>
            <form onSubmit={handleAccountSubmit}>
              <div className="form-group">
                <label className="form-label" htmlFor="register-email">Email</label>
                <input
                  id="register-email"
                  className="form-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="register-password">Password</label>
                <input
                  id="register-password"
                  className="form-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  minLength={6}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-lg w-full"
                disabled={loading}
              >
                {loading ? 'Creating account...' : 'Continue →'}
              </button>
            </form>

            <div className="auth-footer">
              Already have an account?{' '}
              <Link to="/login">Sign in</Link>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <div className="alert alert-info" style={{ marginBottom: 'var(--space-lg)' }}>
              ℹ️ This data is used by the AI model to personalize your workout analysis.
              A heart rate of 160 BPM means something completely different for a 20-year-old
              athlete versus a 60-year-old beginner.
            </div>

            <DemographicForm
              onSubmit={handleDemographicSubmit}
              submitLabel="Complete Setup →"
              loading={loading}
            />
          </>
        )}
      </div>
    </div>
  );
}
