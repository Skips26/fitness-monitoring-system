import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';

export default function Landing() {
  const { user } = useAuth();

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.15 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 24 },
    show: { 
      opacity: 1, 
      y: 0, 
      transition: { type: 'spring', stiffness: 80, damping: 18 } 
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { 
      opacity: 1, 
      y: 0,
      transition: { type: 'spring', stiffness: 60, damping: 18 }
    },
  };

  return (
    <div>
      <motion.section 
        className="landing-hero"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        <motion.h1 variants={itemVariants}>
          Train Smarter with{' '}
          <span className="text-gradient">AI-Powered</span> Insights
        </motion.h1>

        <motion.p variants={itemVariants}>
          Our smart fitness wearable captures your body's biometric data during workouts.
          Advanced AI analyzes your performance to show you exactly how effective
          your training was and what drove those results.
        </motion.p>

        <motion.div className="flex gap-md" variants={itemVariants}>
          {user ? (
            <Link to="/dashboard" className="btn btn-primary btn-lg">
              Go to Dashboard
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
            </Link>
          ) : (
            <>
              <Link to="/register" className="btn btn-primary btn-lg">
                Get Started
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
              </Link>
              <Link to="/login" className="btn btn-secondary btn-lg">
                Sign In
              </Link>
            </>
          )}
        </motion.div>

        <motion.div 
          className="landing-features"
          variants={containerVariants}
        >
          <motion.div 
            className="card feature-card"
            variants={cardVariants}
            whileHover={{ y: -6, transition: { duration: 0.2 } }}
          >
            <div className="feature-icon" style={{ color: 'var(--accent-primary)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
              </svg>
            </div>
            <h3>Heart Rate Tracking</h3>
            <p>
              Monitor your cardiovascular intensity and track your recovery 
              in real-time to optimize your conditioning.
            </p>
          </motion.div>

          <motion.div 
            className="card feature-card"
            variants={cardVariants}
            whileHover={{ y: -6, transition: { duration: 0.2 } }}
          >
            <div className="feature-icon" style={{ color: 'var(--accent-secondary)', background: 'rgba(56, 189, 248, 0.08)', borderColor: 'rgba(56, 189, 248, 0.12)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
            </div>
            <h3>Muscle Engagement</h3>
            <p>
              Track true muscle fatigue and fiber activation to ensure you're 
              pushing hard enough to trigger growth.
            </p>
          </motion.div>

          <motion.div 
            className="card feature-card"
            variants={cardVariants}
            whileHover={{ y: -6, transition: { duration: 0.2 } }}
          >
            <div className="feature-icon" style={{ color: 'var(--accent-success)', background: 'rgba(52, 211, 153, 0.08)', borderColor: 'rgba(52, 211, 153, 0.12)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path>
              </svg>
            </div>
            <h3>Personalized Insights</h3>
            <p>
              Get detailed breakdowns of your workout effectiveness and learn 
              exactly what factors impacted your results.
            </p>
          </motion.div>
        </motion.div>
      </motion.section>
    </div>
  );
}
