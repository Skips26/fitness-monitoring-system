import { useState } from 'react';

export default function DemographicForm({ initialData, onSubmit, submitLabel = 'Save', loading = false }) {
  const [formData, setFormData] = useState({
    first_name: initialData?.first_name || '',
    last_name: initialData?.last_name || '',
    age: initialData?.age || '',
    weight_kg: initialData?.weight_kg || '',
    fitness_level: initialData?.fitness_level || 'medium',
    athlete_type: initialData?.athlete_type || 'gym_bro',
    body_fat_pct: initialData?.body_fat_pct || '',
    limb_length: initialData?.limb_length || 'medium',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...formData,
      age: parseInt(formData.age),
      weight_kg: parseFloat(formData.weight_kg),
      body_fat_pct: parseFloat(formData.body_fat_pct),
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-grid">
        <div className="form-group">
          <label className="form-label" htmlFor="first_name">First Name</label>
          <input
            id="first_name"
            className="form-input"
            type="text"
            name="first_name"
            value={formData.first_name}
            onChange={handleChange}
            placeholder="John"
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="last_name">Last Name</label>
          <input
            id="last_name"
            className="form-input"
            type="text"
            name="last_name"
            value={formData.last_name}
            onChange={handleChange}
            placeholder="Doe"
            required
          />
        </div>
      </div>

      <div className="form-grid">
        <div className="form-group">
          <label className="form-label" htmlFor="age">Age</label>
          <input
            id="age"
            className="form-input"
            type="number"
            name="age"
            value={formData.age}
            onChange={handleChange}
            min="13"
            max="100"
            placeholder="21"
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="weight_kg">Weight (kg)</label>
          <input
            id="weight_kg"
            className="form-input"
            type="number"
            name="weight_kg"
            value={formData.weight_kg}
            onChange={handleChange}
            min="50"
            max="130"
            step="0.1"
            placeholder="80.0"
            required
          />
        </div>
      </div>

      <div className="form-grid">
        <div className="form-group">
          <label className="form-label" htmlFor="body_fat_pct">Body Fat %</label>
          <input
            id="body_fat_pct"
            className="form-input"
            type="number"
            name="body_fat_pct"
            value={formData.body_fat_pct}
            onChange={handleChange}
            min="3"
            max="50"
            step="0.1"
            placeholder="15.0"
            required
          />
        </div>
      </div>

      <div className="form-grid">
        <div className="form-group">
          <label className="form-label" htmlFor="fitness_level">Fitness Level</label>
          <select
            id="fitness_level"
            className="form-select"
            name="fitness_level"
            value={formData.fitness_level}
            onChange={handleChange}
            required
          >
            <option value="low">Low — Beginner / Sedentary</option>
            <option value="medium">Medium — Regular exerciser</option>
            <option value="high">High — Advanced / Athlete</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="athlete_type">Athlete Type</label>
          <select
            id="athlete_type"
            className="form-select"
            name="athlete_type"
            value={formData.athlete_type}
            onChange={handleChange}
            required
          >
            <option value="gym_bro">Gym Bro — Standard lifter</option>
            <option value="powerlifter">Powerlifter — Heavy singles/triples</option>
            <option value="hybrid">Hybrid — Mix of styles</option>
            <option value="non_athletic">Non-Athletic — Casual/beginner</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label" htmlFor="limb_length">Limb Length</label>
        <select
          id="limb_length"
          className="form-select"
          name="limb_length"
          value={formData.limb_length}
          onChange={handleChange}
          required
        >
          <option value="short">Short — Below average limb length</option>
          <option value="medium">Medium — Average limb length</option>
          <option value="long">Long — Above average limb length</option>
        </select>
      </div>

      <button
        type="submit"
        className="btn btn-primary btn-lg w-full mt-lg"
        disabled={loading}
      >
        {loading ? 'Saving...' : submitLabel}
      </button>
    </form>
  );
}
