const FEATURE_ICONS = {
  duration_mins: '⏱️',
  avg_hr: '❤️',
  max_hr: '💗',
  hr_spikes: '📈',
  pct_time_low: '😴',
  avg_emg: '💪',
  emg_fatigue: '🔥',
  total_reps: '🔄',
  age: '🎂',
  fitness_level: '🏋️',
  workout_type: '📋',
  athlete_type: '🏅',
  body_fat_pct: '⚖️',
  limb_length: '📏',
};

export default function ShapExplanation({ topFactors, explanation }) {
  if (!topFactors || topFactors.length === 0) return null;

  // Find the max absolute SHAP value for scaling
  const maxShap = Math.max(...topFactors.map((f) => Math.abs(f.shap_value)));

  return (
    <div className="shap-factors">
      {explanation && (
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 'var(--space-sm)' }}>
          {explanation}
        </p>
      )}

      {topFactors.map((factor, idx) => {
        const barWidth = maxShap > 0 ? (Math.abs(factor.shap_value) / maxShap) * 100 : 0;
        const isPositive = factor.direction === 'positive';

        return (
          <div
            className="shap-factor animate-in"
            key={factor.feature}
            style={{ animationDelay: `${idx * 0.1}s` }}
          >
            <span style={{ fontSize: '1.3rem', minWidth: '32px', textAlign: 'center' }}>
              {FEATURE_ICONS[factor.feature] || '📊'}
            </span>

            <div style={{ flex: 1 }}>
              <div className="shap-factor-name">{factor.description}</div>
              <div className="shap-bar-container" style={{ marginTop: '6px' }}>
                <div
                  className={`shap-bar ${isPositive ? 'positive' : 'negative'}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>

            <span
              style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                color: isPositive ? 'var(--accent-success)' : 'var(--accent-danger)',
                minWidth: '50px',
                textAlign: 'right',
              }}
            >
              {isPositive ? '+' : ''}{factor.shap_value.toFixed(3)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
