"""
Supabase client initialization.

Two clients are available:
  - supabase_client: Uses the anon key (respects Row Level Security)
  - supabase_admin:  Uses the service role key (bypasses RLS, for server-side operations)
"""

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY


def get_supabase_client() -> Client:
    """Public client — respects RLS policies."""
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_supabase_admin() -> Client:
    """Admin client — bypasses RLS, used for server-side operations."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
