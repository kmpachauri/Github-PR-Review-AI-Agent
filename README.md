**GitHub PR Review AI Agent**

An autonomous code-review agent that analyzes GitHub pull requests using an LLM-based agent, processes reviews asynchronously with Celery, and exposes a simple REST API for triggering reviews and fetching results.

---

## 🔥 Overview / Goal

This project accepts a GitHub PR (repo URL + PR number), fetches the diff/changed files, runs a goal-oriented AI agent to analyze the code for style, bugs, performance, and best-practices, and stores structured results for retrieval. Tasks run asynchronously (Celery + Redis/Postgres) so HTTP requests stay fast and non-blocking.

---

## 📂 Project Structure (expected)

```
app/
├── api/
│   └── endpoints/
│       └── review.py        # FastAPI endpoints: /analyze-pr, /status/{id}, /results/{id}
│   └── __init__.py
├── core/
│   ├── config.py            # env loader and config helpers
│   ├── logging.py           # logging setup (structured logging)
│   └── utils.py             # helpers (fetch diffs, format responses)
├── llms/
│   └── openrouter_llm.py    # LLM/agent wrapper (adapter for chosen LLM)
├── models/
│   └── schemas.py           # Pydantic request/response schemas
├── tasks/
│   ├── analyzer.py          # Celery task: run agent, analyze files, store results
│   └── worker.py            # Celery worker entrypoint
├── main.py                  # FastAPI app entrypoint (uvicorn)
├── tests/                   # pytest tests: test_api.py, test_llm.py, test_tasks.py
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## ✅ Features Implemented

- FastAPI endpoints:
  - `POST /analyze-pr` — start an analysis for a repo PR
  - `GET /status/{task_id}` — check status (`pending`, `processing`, `completed`, `failed`)
  - `GET /results/{task_id}` — fetch analysis results once completed
- Asynchronous processing via **Celery** (broker: Redis is typical; Postgres is optional for results)
- LLM agent abstraction layer — OpenRouter API and CREWAI Agent
- Structured JSON results per file + summary
- Unit tests with **pytest**
- Docker + docker-compose for local multi-service run
- Basic logging & error handling
- Multilanguage Code review 

---

## 🛠️ Quick Setup (local)

> This guide assumes you have Python 3.8+, Docker (optional), and Git installed.

1. Clone repository
```bash
git clone https://github.com/kmpachauri/Github-PR-Review-AI-Agent.git
cd Github-PR-Review-AI-Agent
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate       # macOS / Linux
venv\Scripts\activate          # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Copy environment example and update values
```bash
cp .env.example .env
# Edit .env and add real values (GITHUB_TOKEN, LLM_API_KEY, REDIS_URL, etc.)
```

5. Start Redis (for development)
- Option A — Docker:
```bash
docker run -d --name pr_agent_redis -p 6379:6379 redis:6-alpine
```
- Option B — docker-compose
```bash
docker-compose up -d redis
```

6. Start FastAPI app (uvicorn)
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

7. Start Celery worker (in a separate terminal; ensure `.env` is loaded)
```bash
# from project root
export $(cat .env | xargs)  # load env vars into session (linux/Mac)
celery -A app.tasks.worker worker --loglevel=info
```

> If you use docker-compose for the whole stack, `docker-compose up --build` should start API + Redis + worker (if configured).

---

## 🔐 .env.example (copy to `.env` and fill values)

```
# GitHub settings
GITHUB_TOKEN=your_github_personal_access_token_here

# LLM provider config
LLM_PROVIDER=openrouter         # or openai,gemini, huggingface, ollama
LLM_API_KEY=your_llm_api_key_here

# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
REDIS_URL=redis://localhost:6379/0

#If above are not working and running using docker
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
REDIS_URL=redis://redis:6379/0




# Misc
LOG_LEVEL=INFO
MAX_ANALYSIS_FILES=50        # limit for number of files to analyze from PR
TIMEOUT_SECONDS=300          # per-LLM call timeout
```

---

## 🔎 API Documentation & Usage

When the app is running locally, built-in OpenAPI docs are available:

```
Swagger UI: http://localhost:8000/docs
Redoc:       http://localhost:8000/redoc
```

### 1) POST `/analyze-pr`
Trigger analysis for a GitHub pull request.

**Request JSON**
```json
{
  "repo_url": "https://github.com/user/repo",
  "pr_number": 123,
  "github_token": "optional_token" 
}
```

**cURL example**
```bash
curl -X POST "http://localhost:8000/analyze-pr" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url":"https://github.com/owner/repo",
    "pr_number":1
  }'
```

**Example response (immediate)**
```json
{
  "task_id": "e3f1b2a4-....",
  "status": "queued",
}
```

> Note: The API enqueues an async Celery job and returns a `task_id`. Use `/status/{task_id}` and `/results/{task_id}` to follow progress and retrieve output.

### 2) GET `/status/{task_id}`
Check the task processing status.

**Response example**
```json
{
  "task_id": "e3f1b2a4-...",
  "status": "processing",
}
```

### 3) GET `/results/{task_id}`
Retrieve final analysis once status is `completed`.

**Response (completed) example**
```json
{
  "task_id": "e3f1b2a4-...",
  "status": "completed",
  "results": {
    "files": [
      {
        "name": "app/main.py",
        "issues": [
          {
            "type": "style",
            "line": 12,
            "description": "Line exceeds 120 characters",
            "suggestion": "Wrap long expressions or split into helper functions"
          }
        ]
      }
    ],
    "summary": {
      "total_files": 1,
      "total_issues": 1,
      "critical_issues": 0
    }
  }
}
```

---

## 🧭 Task Workflow (what happens after POST `/analyze-pr`)

1. API validates request and enqueues Celery task with PR metadata.  
2. Celery worker:
   - Fetches PR diff and changed files via GitHub API using the `GITHUB_TOKEN` or the supplied token.
   - Downloads file contents (limit by `MAX_ANALYSIS_FILES`).
   - Prepares prompts and context for the LLM agent (calls to `app/llms/...`).
   - Runs analysis agent (crewai adapter) and collects structured findings.
   - Saves results to result backend (Redis) keyed by `task_id` and updates task status to `completed` or `failed` on error.
3. API endpoints `/status` and `/results` query the backend and return structured data.

---

## 🧪 Testing (Step-by-step)

### 1. Unit tests
Run the test suite locally:
```bash
pytest -q
# or run a single test file
pytest tests/test_api.py::test_analyze_pr_endpoint -q
```

### 2. Manual testing via Swagger UI (recommended)

1. Start app and worker (see Quick Setup).
2. Open `http://localhost:8000/docs` in your browser.
3. Find `POST /analyze-pr` endpoint and click **Try it out**.
4. Paste example request body (replace with a real repo and PR):
```json
{
  "repo_url": "https://github.com/owner/repo",
  "pr_number": 1,
  "github_token":"gph_your_github_token"
}
```
5. Execute — you should receive a JSON response with `task_id`.
6. Use `GET /status/{task_id}` to poll the progress until `completed`.
7. Use `GET /results/{task_id}` to view the structured analysis.

### 3. Manual testing via cURL (quick)

- Trigger analysis:
```bash
curl -X POST http://localhost:8000/analyze-pr \
  -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/owner/repo","pr_number":1}'
```
- Poll status:
```bash
curl http://localhost:8000/status/<task_id>
```
- Fetch results:
```bash
curl http://localhost:8000/results/<task_id>
```

> Some LLM calls can be slow — wait a few seconds and re-poll `status` until the task completes.

---

## ⚠️ Common Errors & Troubleshooting (detailed)

**1. `401 Unauthorized` from LLM provider**  
- Cause: `LLM_API_KEY` missing or invalid.  
- Fix: Ensure `.env` contains a valid `LLM_API_KEY` for the specified `LLM_PROVIDER`. Test provider credentials via a direct API call (curl or provider SDK).

**2. `403 Forbidden` or `401` from GitHub API**  
- Cause: GitHub token missing or missing scopes (e.g., `repo` access).  
- Fix: Create a GitHub Personal Access Token with `repo` & `pull_request` scopes and set `GITHUB_TOKEN` in `.env`. Optionally supply `github_token` in request body for ephemeral quotas.

**3. Redis connection errors** (e.g., `ConnectionRefusedError`)  
- Cause: Redis server not running or wrong `REDIS_URL`.  
- Fix: Start Redis (`docker run -d --name redis -p 6379:6379 redis:6-alpine`) and confirm `REDIS_URL` matches.

**4. Celery task stays `pending` and never runs**  
- Cause: Celery worker not started or using wrong broker URL.  
- Fix: Start worker: `celery -A app.tasks.worker worker --loglevel=info`. Ensure `CELERY_BROKER_URL` is same in worker environment.

**5. Task `failed` due to LLM timeout or rate limits**  
- Cause: LLM provider timed out or refused the request.  
- Fix: Increase `TIMEOUT_SECONDS` or add retry/backoff logic in `tasks/analyzer.py`. Implement provider fallback.


**7. Large PRs cause excessive API calls or long runtimes**  
- Fix: Limit files analyzed by `MAX_ANALYSIS_FILES`, or analyze only changed hunks. Queue several smaller tasks for chunks if needed.

---

## 🧠 Design Decisions

- **FastAPI** for the API: async-first, automatic docs, developer ergonomics.  
- **Celery**: battle-tested task queue with many brokers/backends supported.  
- **Redis**: fast broker and good for task state/temporary results. Optionally use Postgres for durable results.  
- **LLM abstraction layer**: the code targets an adapter pattern (`app/llms/*`) so you can swap providers easily (OpenRouter → OpenAI → Ollama).  
- **Structured JSON outputs**: easier to consume by other tools and to perform automated checks.  
- **Modular layout**: api / tasks / llms / core keep responsibilities separated and testable.

---

## 🔭 Future Improvements

- Add a **GitHub App** for automatic PR triggers and granular permissions.  
- Add **results persistence** in PostgreSQL + migrations + retention policy.  
- Add **comment posting to the PR** (threaded comments via GitHub API).  
- Add **language-specific linters** (flake8, eslint) to complement LLM findings.  
- Improve **LLM prompt engineering** and multi-pass analysis (summarize -> deep-check).  
- Add **rate-limiting** and **circuit breaker** for LLM provider failures.  
- Add **web UI** to browse results and annotate issues.

---

## 🧾 Testing Checklist (what reviewers will check)

- [ ] Start API + worker + Redis successfully.  
- [ ] POST `/analyze-pr` returns a `task_id`.  
- [ ] Worker picks up the task and completes (status transitions: pending→processing→completed).  
- [ ] `GET /results/{task_id}` returns properly formatted JSON matching schema in `app/models/schemas.py`.  

---

## 🪪 License
MIT License — see `LICENSE` file in repository.


