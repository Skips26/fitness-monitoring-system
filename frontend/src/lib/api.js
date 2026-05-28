const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

import { supabase } from './supabase';

/**
 * Fetch wrapper that automatically injects the Supabase JWT token.
 */
async function apiFetch(path, options = {}) {
  const { data: { session } } = await supabase.auth.getSession();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ── Profile API ─────────────────────────────────────────────────────────────

export const profileApi = {
  get: () => apiFetch('/profiles/me'),
  create: (data) => apiFetch('/profiles/me', { method: 'POST', body: JSON.stringify(data) }),
  update: (data) => apiFetch('/profiles/me', { method: 'PUT', body: JSON.stringify(data) }),
};

// ── Workouts API ────────────────────────────────────────────────────────────

export const workoutsApi = {
  list: () => apiFetch('/workouts'),
  get: (id) => apiFetch(`/workouts/${id}`),
  setType: (id, workoutType) =>
    apiFetch(`/workouts/${id}/type`, {
      method: 'PUT',
      body: JSON.stringify({ workout_type: workoutType }),
    }),
  analyze: (id) =>
    apiFetch(`/workouts/${id}/analyze`, { method: 'POST' }),
};
