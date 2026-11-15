# SentinelAI

**A governance gateway that sits between a company's people and its LLMs.** Every prompt goes through a checkpoint first. Injection attempts and requests for sensitive data are blocked, and every decision is logged so someone can audit it later.

![A prompt-injection attempt hidden inside an email, blocked by the firewall](docs/screenshots/playground-blocked.png)

## Why I built this

Companies are rolling out internal AI assistants faster than their risk teams can review them. The questions I kept running into were simple ones that no one could answer:

- What are employees actually sending to the model?
- What stops someone, or a document they paste in, from talking the model into leaking data?
- When something goes wrong, can we prove what happened?

SentinelAI is my answer to those three questions, built as one gateway.

## What it does

```mermaid
flowchart LR
    U[Employee app] --> G[FastAPI gateway]
    G --> V[1. Contract check<br/>Pydantic]
    V --> C[2. Injection classifier<br/>DeBERTa, open model]
    C --> E[3. Policy match<br/>embeddings vs. blocked intents]
    E --> M[LLM provider<br/>mock / OpenAI / Anthropic / Ollama]
    C -. blocked .-> A[(Audit log)]
    E -. blocked .-> A
    M --> A
    A --> D[Streamlit dashboard]
```

1. **Contract check.** Every request must say who's asking, from which feature, and with which prompt version. A request without that context is rejected before any model sees it.
2. **Injection classifier.** An open model ([protectai/deberta-v3-base-prompt-injection-v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)) catches the *how*: "ignore your instructions", role-play jailbreaks, instructions hidden in pasted emails, attacks written in other languages.
3. **Policy match.** Each prompt is compared against a library of blocked intents (PII exfiltration, credential leaks, confidential data). The policy team can add or remove intents from the dashboard without a deploy.
4. **Audit trail.** Every allowed and blocked request is logged with the user, feature, matched policy, risk score and latency. Blocked prompts are stored as a SHA-256 hash in the audit log.

## Results

I wrote a 200-prompt evaluation set: 100 attacks across six categories, and 100 normal enterprise requests. The normal requests include 35 security questions that *should* get through, such as "how do I rotate database passwords?". I scored each version of the firewall against the set.

| Firewall version | Attacks caught | Reworded attacks caught | Normal prompts wrongly blocked |
|---|---|---|---|
| v1: embedding match only (as first built) | 21% | 12% | 1% |
| **v2: classifier + embedding match (current)** | **62%** | **58%** | **6%** |

![Eval report: detector scorecard](docs/screenshots/eval-report.png)

By category, the classifier catches **100%** of direct injections, **80%** of obfuscated or hidden ones and **75%** of jailbreaks, in about 10 ms on a CPU.

Run it yourself:

```bash
python -m evals.run_eval
```

The dataset is in [`evals/dataset.jsonl`](evals/dataset.jsonl). Per-prompt results are in [`evals/results.json`](evals/results.json).

## What I learned

**There are two different problems here, and only one of them is a prompt problem.**

- **How something is asked.** This covers injection, jailbreaks and obfuscation. It's a pattern-recognition problem, and a small open classifier solves most of it.
- **What is being asked for.** "Show me the salary bands" or "give me the customer export" read like ordinary questions. Every prompt-level filter I tested missed most of them (13–40% caught). Whether they should be allowed depends on **who is asking**: HR asking about salaries is the job, and an intern asking is an incident.

So the next layer can't be another better filter. It has to be **role-aware policy**: the same access-control thinking companies already apply to their databases, applied to the AI's front door.

## Product decisions and trade-offs

| Decision | Why |
|---|---|
| **Layered checks instead of one model** | Each layer is cheap, explainable and replaceable. When something gets blocked, the dashboard shows *which* layer did it and why, which matters more to a risk team than a single opaque score. |
| **Embedding threshold set to 0.55** | I swept thresholds from 0.30 to 0.90. 0.55 gives the most catches while blocking ≤5% of normal traffic. Going lower trades away too much: catching half the attacks would block 1 in 6 normal prompts. |
| **I accept 6% false positives for now** | A blocked legitimate prompt is an annoyance. A leaked customer file is a reportable incident. But 6% is too high for daily use, so it's the next thing to fix (see roadmap). |
| **Open models only** | No per-call cost, no data leaving the network for screening, and it runs on a laptop CPU. That matters for regulated teams. |
| **Mock provider by default** | The governance layer can be demoed and tested without API keys or spend. Real providers plug in through LiteLLM. |
| **Policy changes without a deploy** | Policy owners (risk, legal, security) aren't engineers. They can add a blocked intent and tune the threshold from the dashboard, and test it in the simulator first. |

**Metrics I track:** attack catch rate, false-positive rate on normal traffic, added latency per request, and blocked requests by category and by feature.

## Screens

| Home: traffic and block rate | Trace Explorer: every decision, auditable |
|---|---|
| ![Home](docs/screenshots/home.png) | ![Trace Explorer](docs/screenshots/trace-explorer.png) |
| **Playground: allowed request** | **Policy Manager: threshold and intents** |
| ![Allowed prompt](docs/screenshots/playground-allowed.png) | ![Policy Manager](docs/screenshots/policy-manager.png) |

## Roadmap

1. **Role-aware policy.** Map `user_id` to a role and allow or block each data category by role. This closes the "what is being asked for" gap.
2. **Intent judge.** Add a small open model (Llama Guard via Ollama) that labels the data category a prompt is reaching for.
3. **Reduce false positives.** Phrases like "ignore the formatting in my notes" trip the classifier. Add a "warn and log" band for borderline scores instead of a hard block.
4. **Output checks.** Scan responses for PII before they reach the user.
5. **Compliance mapping.** Tag each control to the NIST AI RMF and EU AI Act obligations it supports, and export audit reports.

## Run it locally

No accounts needed. It runs fully in memory with the mock provider.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

```bash
REPOSITORY_MODE=memory ENABLE_LANGFUSE=false uvicorn backend.main:app --port 8000
```

In a second terminal:

```bash
streamlit run dashboard/Home.py
```

The first request takes a few seconds while the two models download and load. After that, checks take about 15 ms.

To persist data, set `REPOSITORY_MODE=supabase`, fill in the Supabase and Langfuse keys from `.env.example`, then run `python scripts/migrate.py` and `python scripts/seed_policies.py`.

### Key settings

| Variable | Default | What it does |
|---|---|---|
| `REPOSITORY_MODE` | `memory` | `memory` for local use, `supabase` for persistence |
| `INJECTION_CLASSIFIER_ENABLED` | `true` | Turns layer 2 on or off |
| `INJECTION_CLASSIFIER_THRESHOLD` | `0.5` | Classifier score that triggers a block |
| `FIREWALL_THRESHOLD` | `0.55` | Similarity score that triggers a policy block |
| `DEFAULT_PROVIDER` | `mock` | `mock`, `openai`, `anthropic` or `ollama` |

### Tests

```bash
pytest
```

## Project layout

```text
backend/
  api/v1/routes/   gateway, policies, traces endpoints
  core/            firewall layers, classifier, embeddings, config
  db/              in-memory and Supabase repositories
  services/        LLM router (LiteLLM), Langfuse tracing
dashboard/         Streamlit app: Home, Playground, Trace Explorer, Policy Manager
evals/             labelled dataset, eval harness, results report
scripts/           migrations and policy seeding
docker/            nginx + supervisord for a single-container deploy
```

## Deploy

The Dockerfile runs FastAPI, Streamlit and nginx in one container on port 7860, which suits Hugging Face Docker Spaces. Add the `.env.example` values as Space secrets and keep `DEFAULT_PROVIDER=mock` for a public deployment.

## Known limits

- I wrote the eval prompts myself. Testing against an independent red-team set is next.
- With 15–20 prompts per category, the per-category numbers are directional.
- The dashboard's request log keeps prompt text so traces are readable. A production deployment should redact or hash it, as the audit log already does.
