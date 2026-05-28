import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Landing() {
  const { user } = useAuth();

  return (
    <div>
      <section className="landing-hero">
        <h1 className="animate-in">
          Train Smarter with{' '}
          <span className="text-gradient">AI-Powered</span> Insights
        </h1>

        <p className="animate-in animate-in-delay-1">
          Our IoT wearable belt captures real-time heart rate, muscle activation,
          and motion data. An XGBoost AI model analyzes your workout effectiveness
          with SHAP-powered explanations.
        </p>

        <div className="flex gap-md animate-in animate-in-delay-2">
          {user ? (
            <Link to="/dashboard" className="btn btn-primary btn-lg">
              Go to Dashboard →
            </Link>
          ) : (
            <>
              <Link to="/register" className="btn btn-primary btn-lg">
                Get Started →
              </Link>
              <Link to="/login" className="btn btn-secondary btn-lg">
                Sign In
              </Link>
            </>
          )}
        </div>

        <div className="landing-features animate-in animate-in-delay-3">
          <div className="card feature-card">
            <div className="feature-icon">🫀</div>
            <h3>ECG Heart Monitor</h3>
            <p>
              AD8232 sensor captures real-time electrocardiogram signals.
              Dynamic baseline filtering calculates accurate BPM in real-time.
            </p>
          </div>

          <div className="card feature-card">
            <div className="feature-icon">💪</div>
            <h3>EMG Muscle Tracking</h3>
            <p>
              Electromyography sensor measures muscle fiber recruitment and
              fatigue through a voltage-divider protected circuit.
            </p>
          </div>

          <div className="card feature-card">
            <div className="feature-icon">🤖</div>
            <h3>XGBoost AI Analysis</h3>
            <p>
              A trained classifier predicts workout effectiveness (Low → Maximum)
              with SHAP explanations telling you exactly why.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
