create extension if not exists vector;

create table if not exists blocked_intents (
    id bigserial primary key,
    policy_id text not null unique,
    intent_text text not null,
    category text not null,
    embedding vector(384) not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists audit_log (
    id bigserial primary key,
    trace_id text not null,
    session_id text not null,
    user_id text not null,
    policy_id text,
    similarity_score double precision,
    prompt_hash text not null,
    blocked boolean not null default true,
    timestamp timestamptz not null default now()
);

create table if not exists app_settings (
    id integer primary key,
    firewall_threshold double precision not null default 0.90
);

insert into app_settings (id, firewall_threshold)
values (1, 0.90)
on conflict (id) do nothing;

create table if not exists request_logs (
    id bigserial primary key,
    trace_id text not null unique,
    session_id text not null,
    user_id text not null,
    prompt text not null,
    output text,
    provider text not null,
    model text not null,
    feature_tag text not null,
    prompt_version text not null,
    blocked boolean not null default false,
    policy_id text,
    similarity_score double precision,
    latency_ms double precision not null default 0,
    total_cost_usd double precision not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_blocked_intents_policy_id on blocked_intents(policy_id);
create index if not exists idx_audit_log_user_id on audit_log(user_id);
create index if not exists idx_audit_log_timestamp on audit_log(timestamp desc);
create index if not exists idx_request_logs_provider on request_logs(provider);
create index if not exists idx_request_logs_created_at on request_logs(created_at desc);

create or replace function match_blocked_intents(
    query_embedding vector(384),
    match_threshold double precision,
    match_count integer
)
returns table (
    policy_id text,
    intent_text text,
    category text,
    similarity_score double precision
)
language sql
as $$
    select
        blocked_intents.policy_id,
        blocked_intents.intent_text,
        blocked_intents.category,
        1 - (blocked_intents.embedding <=> query_embedding) as similarity_score
    from blocked_intents
    where blocked_intents.is_active = true
      and 1 - (blocked_intents.embedding <=> query_embedding) >= match_threshold
    order by blocked_intents.embedding <=> query_embedding
    limit match_count;
$$;
