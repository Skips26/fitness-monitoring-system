import { Link } from 'react-router-dom';

const LABEL_COLORS = {
  Low: 'low',
  Moderate: 'moderate',
  High: 'high',
  Maximum: 'maximum',
};

const TYPE_LABELS = {
  HILV: 'High Intensity, Low Volume',
  LIHV: 'Low Intensity, High Volume',
  hypertrophy: 'Hypertrophy',
  endurance_lifting: 'Endurance Lifting',
};

export default function WorkoutCard({ workout }) {
  const date = new Date(workout.recorded_at);
  const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  const isAnalyzed = workout.status === 'analyzed';
  const isPending = workout.status === 'pending';

  return (
    <Link to={`/workout/${workout.id}`} className="workout-card" id={`workout-${workout.id}`}>
      <div className="workout-card-date">
        <div style={{ fontWeight: 600 }}>{dateStr}</div>
        <div>{timeStr}</div>
      </div>

      <div className="workout-card-info">
        <div className="workout-card-type">
          {workout.workout_type ? TYPE_LABELS[workout.workout_type] || workout.workout_type : 'Type not set'}
        </div>
        <div className="workout-card-duration">
          {workout.duration_mins} min · {workout.total_reps} reps · Avg HR {workout.avg_hr}
        </div>
      </div>

      {isPending && !workout.workout_type && (
        <span className="badge badge-pending">Select Type</span>
      )}
      {isPending && workout.workout_type && (
        <span className="badge badge-pending">Ready to Analyze</span>
      )}
      {isAnalyzed && (
        <span className={`badge badge-${LABEL_COLORS[workout.effectiveness_name]}`}>
          {workout.effectiveness_name}
        </span>
      )}

      <div className="workout-card-result">
        {isAnalyzed && (
          <>
            <div
              className="workout-card-label"
              style={{ color: `var(--eff-${LABEL_COLORS[workout.effectiveness_name]})` }}
            >
              {Math.round(workout.confidence * 100)}%
            </div>
            <div className="workout-card-confidence">confidence</div>
          </>
        )}
        {!isAnalyzed && (
          <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </span>
        )}
      </div>
    </Link>
  );
}
