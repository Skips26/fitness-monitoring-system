import { useEffect, useState } from 'react';

const EFFECTIVENESS_COLORS = {
  Low: 'var(--eff-low)',
  Moderate: 'var(--eff-moderate)',
  High: 'var(--eff-high)',
  Maximum: 'var(--eff-maximum)',
};

export default function EffectivenessGauge({ label, confidence, size = 180 }) {
  const [animatedOffset, setAnimatedOffset] = useState(0);

  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const percentage = confidence * 100;
  const targetOffset = circumference - (percentage / 100) * circumference;
  const color = EFFECTIVENESS_COLORS[label] || 'var(--accent-primary)';

  useEffect(() => {
    // Trigger animation after mount
    const timer = setTimeout(() => {
      setAnimatedOffset(targetOffset);
    }, 100);
    return () => clearTimeout(timer);
  }, [targetOffset]);

  return (
    <div className="gauge-container">
      <div className="gauge-ring" style={{ width: size, height: size }}>
        <svg width={size} height={size}>
          <circle
            className="gauge-bg"
            cx={size / 2}
            cy={size / 2}
            r={radius}
          />
          <circle
            className="gauge-fill"
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeDasharray={circumference}
            strokeDashoffset={animatedOffset || circumference}
          />
        </svg>
        <div className="gauge-label">
          <div className="gauge-value" style={{ color }}>
            {Math.round(percentage)}%
          </div>
          <div className="gauge-text">{label}</div>
        </div>
      </div>
    </div>
  );
}
