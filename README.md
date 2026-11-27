# AI Interviewer · InterviewHub

**An AI-assisted interview and recruitment platform built with FastAPI, PostgreSQL, and a locally hosted LLM.**

AI Interviewer began as a small interview simulation project and has grown into a stage-based AI interview engine with structured, evidence-linked feedback. **InterviewHub** extends it with candidate registration, passwordless authentication, administrator authentication with MFA, and controlled interview management.

> **Status: active development — local prototype.** The candidate backend workflow (registration → verification → interview → completion) and administrator authentication are implemented and tested. The unified frontend and administrator interview-review workflow are not yet complete. **Use synthetic test candidates only; this version must not be used to process real applicants or make hiring decisions.**

## Vision

InterviewHub aims to provide a consistent candidate interview experience and make job-relevant interview evidence accessible to authorized human reviewers. AI generates questions and can assist with summaries and feedback, but **human reviewers remain responsible for interpreting the results**. The system is not designed to make automatic hiring or rejection decisions.

The intended user experiences are:

- **Candidate:** Register, verify an email address, sign in without a password, complete a single interview attempt, and receive a completion confirmation.
- **Administrator:** Sign in with password and time-based one-time password (TOTP) MFA, review completed interview transcripts, and request AI-generated summaries and feedback.

The candidate experience is currently available through the **InterviewHub API / Swagger UI**; a dedicated web interface is planned. Administrator authentication is implemented, but interview review through the administrator API is the next milestone.

## Implementation Status

**Legend:** ✅ Implemented · 🚧 In progress / not yet integrated · 📋 Planned

| Area | Status | Details |
| --- | --- | --- |
| Stage-based AI interview engine | ✅ | Background, Motivation, Experience, Technical Foundation, and Problem Solving |
| Local LLM integration | ✅ | Ollama with `gemma3:1b` |
| Interview storage | ✅ | UUID-based JSON records with atomic file replacement for new writes |
| Structured summaries and feedback in the engine | ✅ | Cached summary and Pydantic-validated feedback with references to answers |
| Candidate registration and email verification | ✅ | Normalized email, one-use verification token, Mailpit for local delivery |
| Passwordless candidate login | ✅ | One-use login token and HttpOnly session cookie |
| Administrator authentication | ✅ | Argon2id password hashing, TOTP MFA, encrypted MFA secret, separate administrator sessions |
| Administrator credential rotation | ✅ | Local scripts for password and MFA changes; session revocation |
| Interview attempts | ✅ | PostgreSQL uniqueness constraint enforces one attempt per candidate |
| InterviewHub → AI engine integration | ✅ | Internal API key, stable interview IDs, authenticated candidate gateway |
| Interview recovery | ✅ | Candidate can retrieve the active question and stage after refresh |
| Answer submission and completion | ✅ | Question-number-based idempotency, locked state changes, stage transitions, completion tracking |
| Legacy AI engine endpoint protection | ✅ | Internal-key authentication; no longer directly usable by the standalone browser UI |
| Administrator transcript review | 📋 | Protected list and details for completed interviews |
| Administrator summary and feedback access | 📋 | Gate generation and viewing behind administrator authorization |
| Unified candidate and admin frontend | 📋 | Planned React + TypeScript interface |
| Abuse prevention, CSRF and audit logs | 📋 | Additional controls needed before any non-local use |
| Automated CI, deployment and monitoring | 📋 | Reproducible deployment and operational safeguards not yet implemented |

> The main development work described here is on **`feature/interview-hub-setup`** and is not yet merged into `main`.

## Why This Project?

An AI interview application requires more than sending prompts to a language model. It must track a multi-stage conversation, preserve context, validate model output, handle interruptions and retries, manage identities, and protect candidate information.

Running the model locally through Ollama offers an environment for learning and experimentation without per-request API fees. A small model also has limitations: question and evaluation quality can vary. The project therefore combines application-controlled stages, response validation, testable persistence, and explicit separation between AI-generated observations and human assessment.

## Architecture

This repository is a monorepo with two FastAPI services:

```text
AI-interviewer/
├── backend/                      # Original AI interview engine
│   ├── main.py                   # Protected AI engine endpoints
│   ├── models/                   # Interview stages and feedback models
│   ├── prompts/                  # Interview and evaluation prompts
│   └── services/                 # LLM, interview logic, storage and analysis
├── frontend/                     # Legacy standalone UI (not integrated)
├── tests/                        # AI engine and endpoint security tests
├── interview-hub/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py           # Candidate / administrator API
│   │   │   ├── models/          # SQLAlchemy models
│   │   │   ├── schemas/         # Request / response validation
│   │   │   └── services/        # Authentication and AI engine HTTP client
│   │   ├── migrations/          # Alembic schema versions
│   │   └── tests/               # API, service and PostgreSQL integration tests
│   └── docker-compose.yml       # PostgreSQL and Mailpit
├── docker-compose.yml           # AI engine, Ollama and legacy frontend
└── README.md
```

**Current local request path:**

```text
Candidate / Swagger UI (:8001)
          │
          ▼
 InterviewHub FastAPI
 ├── PostgreSQL (:5433)
 │    ├── candidates and email verification / login tokens
 │    ├── candidate and administrator sessions
 │    └── one interview attempt per candidate
 └── authenticated service-to-service HTTP
          │
          ▼
 AI Interviewer FastAPI (:8000)
 ├── Ollama / gemma3:1b
 └── local interview JSON records
```

Both candidate and administrator cookies are handled by InterviewHub. **The browser never receives the internal AI engine API key.** The engine is bound to the loopback interface for local development, and protected internal endpoints validate the shared key. This is not a complete production network isolation design.

The old standalone frontend under `frontend/` still calls legacy engine routes directly. Those routes now require an internal API key, so **the legacy UI is no longer a functional end-to-end entry point**. A new candidate/admin frontend is planned for InterviewHub; do not place the internal API key in browser code to restore the old UI.

## Candidate Interview Lifecycle

1. **Register:** `POST /candidates` validates and stores candidate details. Registration creates a one-use email verification token.
2. **Verify:** `POST /auth/verify-email` verifies the token and creates a candidate session. Verified candidates can later request passwordless login tokens.
3. **Reserve:** `POST /interviews/attempt` creates or retrieves the candidate's sole PostgreSQL attempt. A unique constraint on `candidate_id` enforces the restriction even under competing inserts.
4. **Start:** `POST /interviews/start` calls a protected AI engine endpoint using a stable interview ID. A retry recovers the same interview rather than generating another one.
5. **Resume:** `GET /interviews/current` returns the candidate's current stage, active question, and question number without generating new content.
6. **Answer:** `POST /interviews/answer` accepts a numbered answer. Repeating the same submission does not duplicate the answer or advance the stage twice. A conflicting answer to an already-answered question is rejected.
7. **Finish:** After the fifth answer the AI engine enters `SUMMARY`; InterviewHub records the attempt as `completed`. Summary generation and review are separate from the candidate's completion event.

The five question stages are **Background → Motivation → Experience → Technical Foundation → Problem Solving**. Stage progression is controlled by application code, not by the LLM.

### Reliability decisions

- **Database uniqueness:** The single-attempt rule is enforced by PostgreSQL, not only by an application-level check.
- **Stable interview IDs:** Repeated starts use the reserved attempt's interview ID, preventing duplicate AI sessions.
- **Question-number idempotency:** The engine recognizes a repeated answer to the same question; differing answers for an answered question cause a conflict.
- **Locks:** Per-interview file locks serialize state-changing engine operations, and PostgreSQL row locking protects updates to individual attempts.
- **Save before generation:** An accepted answer is persisted before asking Ollama for the next question. If generation fails, the same submission can be retried without losing the answer.
- **Atomic JSON writes:** A temporary file is written and replaced into place to reduce the chance of incomplete interview records after interrupted writes.

These mechanisms improve the local prototype but do not provide distributed transactions across PostgreSQL and the JSON store. Cross-service reconciliation, complete concurrency coverage, and recovery testing remain future work.

## Authentication and Access Boundaries

**Candidates:** Email verification and passwordless login use one-use, expiring tokens. Candidate sessions use opaque tokens stored as hashes server-side and sent through HttpOnly cookies. Candidate interview endpoints derive the owner from the authenticated session; the browser does not choose a candidate ID or AI interview ID.

**Administrators:** An administrator authenticates with a password hashed using Argon2id and a TOTP code. MFA secrets are encrypted at rest with a locally configured Fernet key. Administrator sessions are separate from candidate sessions, and tools exist for credential rotation. The administrator interview review routes are still being implemented.

**AI engine:** Internal operations use a server-to-server API key. Original direct interview, answer, summary, and feedback routes are now gated with the same internal-key check and excluded from the public OpenAPI schema. This prevents unauthenticated direct calls; it does not replace network isolation, secret rotation, or additional production controls.

## AI Summaries, Feedback and Responsible Use

The original AI engine supports summary generation and structured feedback once the interview is complete. Its feedback pipeline:

1. Numbers the candidate answers in the prompt.
2. Requests structured observations from Ollama.
3. Uses Pydantic to validate the response structure.
4. Checks that referenced answer IDs exist and resolves them to the actual answer text.
5. Caches the validated feedback with the interview record.

This prevents the system from fabricating evidence *quotations* by copying model-generated text, but **does not establish that every observation is supported by the evidence**. Small local models may still produce generic, inconsistent, or misleading evaluations.

Experimental keyword extraction and rule-based sentiment analysis are not reliable hiring signals and must not be used to rank candidates. The next milestones will integrate summaries and feedback into **administrator-only**, human-reviewed workflows.

## API Reference (InterviewHub)

All paths below refer to the InterviewHub FastAPI service on `http://127.0.0.1:8001`.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | Public (local) | Application health |
| `GET` | `/health/database` | Public (local) | Database connectivity |
| `POST` | `/candidates` | Public | Candidate registration and verification email |
| `POST` | `/auth/verify-email` | Token | Verify email and establish session |
| `POST` | `/auth/request-login` | Public | Request a one-use login email |
| `POST` | `/auth/complete-login` | Token | Exchange login token for candidate session |
| `GET` | `/auth/me` | Candidate | Current candidate profile |
| `POST` | `/auth/logout` | Candidate session | Revoke candidate session |
| `POST` | `/interviews/attempt` | Candidate | Create/retrieve sole attempt |
| `POST` | `/interviews/start` | Candidate | Start or recover AI interview |
| `GET` | `/interviews/current` | Candidate | Current attempt and active question |
| `POST` | `/interviews/answer` | Candidate | Submit an answer to a numbered question |
| `POST` | `/admin/auth/login` | Password + TOTP | Create administrator session |
| `GET` | `/admin/auth/me` | Administrator | Current administrator profile |
| `POST` | `/admin/auth/logout` | Administrator session | Revoke administrator session |

> `GET /admin/interviews` and `GET /admin/interviews/{attempt_id}` are **next-milestone endpoints**, not part of the completed API described here.

## Technology Stack

| Component | Technology |
| --- | --- |
| AI interview engine | Python 3.12, FastAPI, Pydantic |
| Local AI inference | Ollama, `gemma3:1b` |
| InterviewHub backend | Python, FastAPI, HTTPX, Pydantic |
| Relational persistence | PostgreSQL 17, SQLAlchemy, Psycopg, Alembic |
| Authentication | Argon2id, TOTP (PyOTP), Fernet, hashed session tokens |
| Development email | SMTP + Mailpit |
| Interview state persistence | JSON files, file locking, atomic replacement |
| Testing | pytest, FastAPI TestClient, HTTPX, PostgreSQL integration tests |
| Local orchestration | Docker Compose |
| Planned unified UI | React, TypeScript |

## Run Locally

> **Development use only.** These instructions assume Linux or WSL, Python 3.12, Docker Compose, and synthetic test data. Never commit secrets or real candidate records.

### 1. Configure environment files

Create a repository-root `.env` for the AI engine. Generate a random secret locally (do not reuse the example text):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

```dotenv
# AI-interviewer/.env
AI_ENGINE_INTERNAL_KEY=<random-shared-internal-key>
```

Create `interview-hub/.env` with the same internal key and your local PostgreSQL credentials:

```dotenv
POSTGRES_DB=interviewhub
POSTGRES_USER=interviewhub
POSTGRES_PASSWORD=<strong-local-password>
AI_ENGINE_INTERNAL_KEY=<same-random-shared-internal-key>
AI_ENGINE_URL=http://127.0.0.1:8000
INTERVIEW_TOPIC=Software Engineering
ADMIN_MFA_ENCRYPTION_KEY=<fernet-key-generated-locally>
SESSION_COOKIE_SECURE=false
SMTP_HOST=127.0.0.1
SMTP_PORT=1025
MAIL_FROM=no-reply@interviewhub.local
```

Generate a Fernet key using the installed Python dependencies:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Never overwrite a Fernet key currently protecting existing administrator MFA secrets** without a planned rotation. `SESSION_COOKIE_SECURE=false` is for local HTTP testing only; production must use HTTPS and secure cookies.

Check that both `.env` files are ignored by Git:

```bash
git check-ignore .env interview-hub/.env
```

### 2. Start Ollama and the AI engine

From the repository root:

```bash
docker compose up -d --build ollama backend
docker exec ai-interviewer-ollama ollama list
```

If `gemma3:1b` is missing:

```bash
docker exec ai-interviewer-ollama ollama pull gemma3:1b
```

The AI engine listens on **http://127.0.0.1:8000**. Its protected legacy routes are not meant for direct browser use.

### 3. Start PostgreSQL and Mailpit

From `interview-hub/`:

```bash
docker compose up -d db mailpit
docker compose ps
```

PostgreSQL listens locally on **127.0.0.1:5433**. Mailpit's test inbox is at **http://127.0.0.1:8025**, with SMTP on port 1025.

### 4. Start InterviewHub

From `interview-hub/backend/` in a Python 3.12 virtual environment:

```bash
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Open **http://127.0.0.1:8001/docs** for the candidate and administrator APIs.

The application currently connects to PostgreSQL using localhost:5433 and communicates with the Docker-hosted AI engine using localhost:8000. Those addresses are specifically for this host/WSL development setup.

### 5. Set up an administrator (optional)

From `interview-hub/backend/`:

```bash
python -m app.scripts.create_admin
python -m app.scripts.enroll_admin_mfa
```

These scripts prompt for sensitive credentials locally. Do not paste passwords, TOTP secrets, recovery details, or token values into logs or issue trackers. Additional scripts support password changes and MFA rotation.

### 6. Run automated tests

AI engine tests (repository root):

```bash
python -m pytest tests/ -q
```

InterviewHub tests (`interview-hub/backend/`):

```bash
python -m pytest -q
```

InterviewHub's PostgreSQL integration tests require a separate local database named `interviewhub_test`. Do not point the test suite at the development or production database. The test suite includes security, authentication, database-constraint, API, and failure-recovery coverage; some cases mock Ollama to keep tests deterministic.

### 7. Test the candidate flow

In InterviewHub Swagger UI, register a synthetic candidate, use Mailpit to retrieve the verification token, call `/auth/verify-email`, reserve or start the interview, and submit each numbered answer through `/interviews/answer`. Use `/interviews/current` to check state recovery and completion.

## Roadmap

The next implementation milestones are:

1. **Administrator interview review:** Protected completed-interview list and transcript access.
2. **Administrator-only summary and feedback:** Integrate the existing engine's report generation; add caching, locking, consistency checks and clearer completion semantics.
3. **Candidate frontend:** Unified registration, verification, login, interview, recovery and completion experience.
4. **Administrator dashboard:** MFA login, candidate list, transcript and AI-assisted review interface.
5. **Security and reliability:** CSRF defenses for cookie-based actions, login and registration rate limiting, audit logging, concurrency/reconciliation tests, retention and deletion policies.
6. **CI/CD, deployment and documentation:** Automated test pipeline, reproducible environment, deployment safeguards, screenshots, architecture review and demo documentation.

## Known Limitations

- **Not production-ready:** The application is a local prototype; do not process real applicants or make employment decisions using its outputs.
- **Frontend gap:** The legacy standalone UI uses routes that now require internal authentication. There is not yet a fully integrated candidate/admin web portal.
- **Administrator review gap:** Password + MFA login works, but protected interview listing, transcripts, summary access, and review dashboard remain to be completed.
- **Split persistence:** InterviewHub tracks attempts in PostgreSQL while interview content remains in JSON files. Cross-service reconciliation, backups, retention and deletion workflows are not yet complete.
- **Operational security:** Rate limiting, CSRF protection, fine-grained audit logs, HTTPS deployment and isolated private networking are not yet in place. Internal-key authentication and localhost bindings are development safeguards.
- **Evaluation limitations:** A referenced answer may not logically support an AI observation. Small local models can produce inconsistencies, and evaluation quality and fairness have not been validated for real hiring.
- **Privacy:** Candidate age is currently collected by the prototype schema; its necessity should be reviewed under data-minimization principles. Age and experimental sentiment analysis must not be used to rank or reject candidates.
- **Deployment:** No production-grade CI/CD pipeline, monitoring, disaster recovery plan or GDPR-aligned operational process has been completed.

## Development Workflow

Work is developed and tested incrementally on feature branches. The current InterviewHub work is on `feature/interview-hub-setup`; significant milestones are committed only after automated checks and manual verification. Documentation is updated when behavior changes, with implemented functionality clearly distinguished from planned work.

---

*Originally a Mini AI Interviewer assignment; now expanding into InterviewHub, an AI-assisted recruitment prototype designed around secure candidate workflows and human oversight.*
