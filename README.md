# SentinelAI

SentinelAI is a portfolio-ready LLM governance layer built around three ideas:

- validate every request before it reaches a model
- block unsafe prompts with a semantic firewall backed by Supabase pgvector
- make traffic observable through Langfuse plus a simple Streamlit dashboard

## What is included

- FastAPI gateway with `POST /api/v1/gateway/chat` and `POST /api/v1/gateway/mock`
- Prompt contract validation via Pydantic
- Semantic firewall using `sentence-transformers/all-MiniLM-L6-v2`
- Supabase tables for policies, audit logs, settings, and request logs
- Langfuse trace logging with graceful degradation if tracing fails
- Streamlit dashboard with Home, Trace Explorer, and Policy Manager pages
- Seed script for adversarial policies
- Regression tests for safe and blocked prompts
- Docker assets for Hugging Face Docker Spaces

## Architecture

```text
Client -> FastAPI Gateway -> Semantic Firewall -> Mock/Real Provider
                             |                  |
                             v                  v
                        Supabase pgvector    Langfuse
                             |
                             v
                      Streamlit Dashboard
```

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment template:

```bash
cp .env.example .env
```

4. Run the SQL migrations against Supabase:

```bash
python scripts/migrate.py
```

5. Seed the blocked intent policies:

```bash
python scripts/seed_policies.py
```

6. Start the backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

7. Start the dashboard in a second terminal:

```bash
streamlit run dashboard/Home.py
```

## Demo flow

1. Send a safe prompt to `POST /api/v1/gateway/mock`.
2. Send an unsafe prompt that should trigger the firewall.
3. Open the dashboard and inspect request counts, recent traces, and policy matches.

## Hugging Face deployment

This repo includes a Docker-based deployment setup for Hugging Face Spaces. The container runs:

- FastAPI on port `8000`
- Streamlit on port `8501`
- Nginx as the public entrypoint on port `7860`

Add the environment variables from `.env.example` as Hugging Face Space Secrets, keep `DEFAULT_PROVIDER=mock`, and choose the Docker Space runtime.

## Recommended screenshots

- Home dashboard
- Trace Explorer with one blocked and one successful prompt
- Policy Manager with the threshold slider and simulator

## Notes

- `request_logs` is included as a lightweight Supabase-backed trace cache for the dashboard.
- Langfuse remains the observability layer, but the dashboard does not break if Langfuse is temporarily unavailable.
- Real provider routing is intentionally minimal for this MVP. Hosted demos should stay on `mock` mode.
