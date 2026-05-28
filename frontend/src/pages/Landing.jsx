import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';

export default function Landing() {
  const { user } = useAuth();

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    show: { 
      opacity: 1, 
      y: 0, 
      transition: { 
        type: 'spring', 
        stiffness: 70, 
        damping: 15 
      } 
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, scale: 0.9 },
    show: { 
      opacity: 1, 
      scale: 1,
      transition: { type: 'spring', stiffness: 50, damping: 15 }
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
        <motion.div 
          className="hero-glow"
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{
            position: 'absolute',
            top: '20%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '600px',
            height: '600px',
            background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)',
            pointerEvents: 'none',
            zIndex: -1,
            borderRadius: '50%'
          }}
        />

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
        </motion.div>

        <motion.div 
          className="landing-features"
          variants={containerVariants}
        >
          <motion.div 
            className="card feature-card"
            variants={cardVariants}
            whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(99, 102, 241, 0.1)' }}
          >
            <div className="feature-icon" style={{ color: 'var(--accent-primary)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
            whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(6, 182, 212, 0.1)' }}
          >
            <div className="feature-icon" style={{ color: 'var(--accent-secondary)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
            whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(16, 185, 129, 0.1)' }}
          >
            <div className="feature-icon" style={{ color: 'var(--accent-success)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
