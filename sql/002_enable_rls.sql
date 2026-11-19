-- Block direct access through Supabase's public REST API (anon/authenticated roles).
-- No policies are added: only the backend's service-role key, which bypasses RLS, can read or write.
alter table blocked_intents enable row level security;
alter table audit_log enable row level security;
alter table app_settings enable row level security;
alter table request_logs enable row level security;

-- The match function runs with the caller's rights, so keep it away from the public roles too.
revoke execute on function match_blocked_intents(vector, double precision, integer) from public, anon, authenticated;
