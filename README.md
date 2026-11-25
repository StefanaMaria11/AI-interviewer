# AI Interviewer · InterviewHub

**An evolving AI-powered interview and recruitment platform built with FastAPI, local LLMs, and PostgreSQL.**

AI Interviewer began as a *Mini AI Interviewer* assignment: a small application that asks interview questions and summarizes the responses. It has since grown into a stage-based interview engine with structured, evidence-linked feedback. The next phase, **InterviewHub**, adds the candidate and administrator workflows needed to make those capabilities part of one cohesive recruitment application.

> **Development status:** Active development / local prototype. The AI interview engine is functional. InterviewHub's backend foundation and candidate registration API are implemented, but its frontend, email verification, authentication, and integration with the AI engine are not complete. **Do not use this version to process real applicants or make hiring decisions.**

## Vision

The aim is to provide a consistent, accessible interview experience for candidates while helping recruiters review structured, job-relevant information. AI can assist with questions, summaries, and evidence-based observations; **human reviewers remain responsible for interpreting results and making recruitment decisions**.

The finished application is intended to support two user experiences:

- **Candidates:** Register, verify their email without creating a password, complete one interview attempt, and see a submission confirmation.
- **Administrators:** Sign in securely, review applicants and interview transcripts, view summaries and feedback, and carry out human-led assessments.

These are **planned workflows**, not yet available end to end.

## Implementation Status

The project is under active development. Core AI Interviewer functionality is implemented, while InterviewHub is being developed incrementally on the `feature/interview-hub-setup` branch.

**Status legend:** ✅ Implemented · 🚧 In Progress · 📋 Planned

| Area | Status | Notes |
|---|---|---|
| **AI Interview Engine** | | |
| Stage-based AI interviews | ✅ Implemented | Background, Motivation, Experience, Technical Foundation, and Problem Solving |
| Local LLM integration | ✅ Implemented | Ollama with `gemma3:1b` |
| Interview transcript persistence | ✅ Implemented | UUID-based interviews stored in local JSON files |
| AI-generated summaries | ✅ Implemented | Summaries generated after interview completion |
| Structured interview feedback | ✅ Implemented | Pydantic-validated strengths, improvements, and overall feedback |
| Evidence-based feedback | ✅ Implemented | Answer references validated and resolved to original candidate responses |
| Feedback quality improvements | 🚧 In Progress | Improving consistency, relevance, and accuracy across interview stages |
| **InterviewHub Foundation** | | |
| InterviewHub FastAPI backend | ✅ Implemented | Independent backend under `interview-hub/backend/` |
| PostgreSQL and SQLAlchemy | ✅ Implemented | Database configuration, ORM models, and session management |
| Alembic migrations | ✅ Implemented | Version-controlled database schema with the initial Candidates table |
| Candidate registration API | ✅ Implemented | Input validation, email normalization, uniqueness constraints, and duplicate handling |
| Automated registration tests | ✅ Implemented | Schema and API tests |
| Email verification | 🚧 In Progress | Token model created; verification workflow and email delivery pending |
| **Authentication and Interview Security** | | |
| Administrator authentication | 📋 Planned | Secure login, password hashing, MFA, and session management |
| Candidate passwordless authentication | 📋 Planned | Single-use verification links and secure candidate sessions |
| Role-based access control | 📋 Planned | Protected endpoints and administrator-only access to evaluations |
| Bot and abuse prevention | 📋 Planned | Cloudflare Turnstile, rate limiting, and registration abuse protection |
| Interview attempt enforcement | 📋 Planned | One interview attempt per verified candidate, enforced server-side |
| Interview session recovery | 📋 Planned | Restore interrupted sessions without creating additional attempts |
| **Unified Recruitment Platform** | | |
| React and TypeScript frontend | 📋 Planned | Responsive application with separate candidate and administrator interfaces |
| AI Interviewer integration | 📋 Planned | Secure communication between InterviewHub and the AI engine |
| Candidate management dashboard | 📋 Planned | Candidate records, interview progress, transcripts, and results |
| Interview monitoring and administration | 📋 Planned | Interview status tracking and administrative review tools |
| **AI Evaluation and Responsible Recruitment** | | |
| Role-specific evaluation criteria | 📋 Planned | Assessments grounded in job requirements and interview evidence |
| AI-assisted candidate review | 📋 Planned | Explainable observations to support human recruitment decisions |
| Prompt injection protection | 📋 Planned | Additional safeguards, input isolation, and output validation |
| Evaluation consistency and fairness | 📋 Planned | Bias testing, reliability checks, and human oversight |
| **Production Readiness** | | |
| Security hardening | 📋 Planned | HTTPS, encryption, CSRF protection, security headers, and secrets management |
| Audit logging and monitoring | 📋 Planned | Authentication events, administrative activity, and system monitoring |
| Privacy and data management | 📋 Planned | GDPR-aligned safeguards, data retention, deletion, and access policies |
| Automated security testing | 📋 Planned | Vulnerability scanning, dependency checks, and security testing |
| CI/CD and deployment | 📋 Planned | Automated workflows, production deployment, and backup and recovery mechanisms |

> **Development note:** InterviewHub features are currently available only on `feature/interview-hub-setup` until integrated into `main`. The application remains a development prototype and is not yet suitable for processing real recruitment applications or making employment decisions.

## Why This Project?

The original assignment was an opportunity to experiment with practical LLM application development instead of a purely conversational demo. I chose a job-interview scenario because it requires more than text generation: the system must track state, preserve context, manage data, validate model output, and expose useful results through an interface.

Running a model locally through Ollama also provides an environment for experimenting without paying per API request. This has practical trade-offs: smaller local models can be less consistent, particularly when generating evaluative feedback. Those limitations have directly informed the application's design, testing, and validation strategies.

InterviewHub extends that work into a full-stack project, with candidate registration, a relational database, authentication, authorization, and eventually an administrative review workflow.

## Architecture

The codebase is a **monorepo** containing two application components being developed toward a single product:

```text
AI-interviewer/
├── backend/                    # Existing AI interview engine (FastAPI)
│   ├── models/                 # Interview and feedback schemas
│   ├── prompts/                # Stage, summary, and feedback prompts
│   ├── services/               # Interview, LLM, analysis, and storage logic
│   └── main.py                 # AI engine API
├── frontend/                   # Current standalone interview interface
├── tests/                      # AI engine tests
├── interview-hub/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   ├── schemas/        # Pydantic request validation
│   │   │   ├── database.py     # Database engine and session dependency
│   │   │   └── main.py         # InterviewHub API
│   │   ├── migrations/         # Alembic schema history
│   │   ├── tests/              # InterviewHub backend tests
│   │   └── requirements.txt
│   ├── frontend/               # Planned candidate/admin portal
│   └── docker-compose.yml     # Development PostgreSQL container
├── docker-compose.yml         # AI engine, current frontend, Ollama
└── README.md
```

**Current local setup**

```text
Standalone interview UI (:5000)
           │
           ▼
AI Interviewer FastAPI (:8000) ──► Ollama (local model)
           │
           ▼
   JSON interview records

InterviewHub FastAPI (:8001) ──► PostgreSQL (localhost:5433)
       Candidate registration
```

**Target integration (planned)**

```text
       Unified InterviewHub web portal
          /                    \
    Candidate views         Admin views
          \                    /
           ▼                  ▼
         InterviewHub platform API
         ├── Authentication & permissions
         ├── Candidate / attempt management
         ├── PostgreSQL
         └── Protected requests to AI Interviewer
                                  └── Ollama
```

The platform API should act as the authorized gateway to interview content. The AI engine's transcript, summary, and feedback endpoints are **not yet access-controlled** and must not be publicly exposed in the current form.

## AI Interview Engine

### Interview workflow

The engine follows predefined stages rather than allowing the model to control the overall process:

1. **Background** — education and professional situation.
2. **Motivation** — interest in the position and field.
3. **Experience** — practical work and projects.
4. **Technical Foundation** — relevant technical reasoning.
5. **Problem Solving** — approach to diagnosing and resolving challenges.
6. **Summary** — generation of the interview report, followed by completion.

Prompts specify interviewer behavior, question rules, stage instructions, and earlier conversation context. The service tracks stage transitions and stores questions and answers under a UUID. The API rejects answers submitted after the interview has finished.

### Structured feedback and evidence

The feedback pipeline separates AI generation from application-side validation:

1. Candidate answers are numbered in the feedback prompt.
2. Ollama returns structured observations with an `answer_id` for each point.
3. Pydantic validates the response shape.
4. Python checks that referenced answer IDs exist and resolves them to the original answer text.
5. Validated feedback is cached with the interview record.

This design prevents fabricated **evidence quotations** caused by the model copying or reformatting candidate text. It **does not prove** an observation is logically supported by the cited answer; that remains an evaluation-quality challenge.

Prompt rules also encourage cross-answer consistency, constructive suggestions, and avoiding unsupported conclusions. Model limitations can still produce generic, repetitive, or contradictory feedback.

### Additional analysis

The engine also stores lightweight keyword extraction and rule-based sentiment analysis. These are experimental supporting signals, **not reliable measures of personality or applicant suitability**, and should not determine hiring outcomes.

## InterviewHub Backend

The InterviewHub service currently provides:

- Candidate registration with Pydantic validation.
- Email normalization and a unique-email database constraint.
- PostgreSQL persistence through SQLAlchemy.
- Database migrations managed by Alembic.
- API and database health checks.
- Automated schema and registration endpoint tests.

**Current development API**

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service health |
| `GET` | `/health/database` | Database connectivity |
| `POST` | `/candidates` | Register a candidate; does **not** verify their email or authorize an interview |

The registration endpoint currently returns a candidate ID and an unverified status. It is **development-only** until email verification, rate limiting, and access controls are implemented.

### Database development

PostgreSQL runs in a Docker container. SQLAlchemy defines models and manages sessions; Alembic versions schema changes so they can be reviewed and applied consistently.

The committed schema currently includes a `candidates` table. A separate email-verification-token model is being developed; its migration and verification workflow are not yet complete.

The prototype registration schema currently includes a declared age field. Before using real candidate data, its necessity should be reviewed under data-minimization principles. Age must not be used to rank or assess candidates.

## Technology Stack

| Component | Technologies |
| --- | --- |
| AI engine API | Python, FastAPI, Pydantic |
| AI inference | Ollama, `gemma3:1b` |
| Current interview UI | HTML, CSS, JavaScript |
| InterviewHub API | Python, FastAPI, Pydantic |
| InterviewHub persistence | PostgreSQL 17, SQLAlchemy, Psycopg |
| Database migrations | Alembic |
| Testing | pytest, FastAPI TestClient / HTTPX, mocks |
| Local orchestration | Docker, Docker Compose |
| Planned unified portal | React, TypeScript |

## Run Locally

> These instructions describe the **current development setup**. InterviewHub and the AI engine are not yet integrated into a single login-based workflow. Do not supply real candidate information.

### Prerequisites

- Docker and Docker Compose.
- Python 3.12 for local InterviewHub backend development.
- Enough local RAM and disk space for Ollama and the selected model.

### Start AI Interviewer

From the repository root:

```bash
docker compose up -d --build
```

Pull the configured model if it is not already installed:

```bash
docker exec ai-interviewer-ollama ollama pull gemma3:1b
```

Open the existing frontend at **http://localhost:5000**. The AI API is available at **http://localhost:8000/docs**.

To stop the AI Interviewer containers:

```bash
docker compose down
```

### Start the InterviewHub database

Create `interview-hub/.env` locally (this file must **never** be committed):

```dotenv
POSTGRES_DB=interviewhub
POSTGRES_USER=interviewhub
POSTGRES_PASSWORD=<replace-with-a-strong-random-password>
```

From `interview-hub/`:

```bash
docker compose up -d db
docker compose ps
```

PostgreSQL is bound to **127.0.0.1:5433** for local development. Its database files persist in a Docker named volume.

### Start the InterviewHub API

From `interview-hub/backend/`, in a Python virtual environment with the dependencies installed:

```bash
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8001
```

Open **http://localhost:8001/docs** for the InterviewHub API documentation, or **http://localhost:8001/health/database** to verify the database connection.

The current database settings assume the API runs directly on the host/WSL and PostgreSQL runs in Docker. These settings will need updating when the platform API itself is containerized.

### Run tests

AI engine tests, from the repository root:

```bash
python -m pytest tests/ -q
```

InterviewHub tests, from `interview-hub/backend/`:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The InterviewHub API tests mock the database session; they do not replace a full PostgreSQL integration-test suite.

## Development Roadmap

The project is being developed incrementally, evolving from a standalone AI interviewer into a secure, scalable, AI-powered recruitment platform. Each phase introduces new functionality while prioritizing security, reliability, candidate privacy, and responsible AI usage.

### Phase 1 — Foundation and Candidate Onboarding

Establish the InterviewHub backend, PostgreSQL database, and Alembic migrations. Implement candidate registration, passwordless email verification, secure token management, and input validation. Introduce initial security measures, including Cloudflare Turnstile, rate limiting, and protection against automated registrations and abuse.

### Phase 2 — Authentication and Interview Management

Implement secure administrator authentication with multi-factor authentication (MFA), role-based access control (RBAC), and protected API endpoints. Introduce secure session management, single-attempt interview enforcement, session recovery, and interview status tracking. Ensure that candidate information, transcripts, summaries, and evaluations are accessible only to authorized users.

### Phase 3 — Unified Web Application

Develop a modern, responsive interface using React and TypeScript. Integrate the AI Interviewer engine with InterviewHub to provide a seamless candidate interview experience and a dedicated administrator dashboard. Include candidate management, interview monitoring, and evaluation review, alongside secure API communication and frontend protections against common web vulnerabilities.

### Phase 4 — AI Evaluation and Recruitment Tools

Improve the accuracy, consistency, and explainability of AI-generated summaries and feedback. Introduce job-specific evaluation criteria, evidence-based candidate assessments, and tools for reviewing and comparing applicants. Strengthen AI security through prompt injection defenses, output validation, bias testing, and evaluation consistency checks. Ensure human oversight, transparency, and responsible AI-assisted recruitment decisions.

### Phase 5 — Testing, Security, and Deployment

Prepare the application for production through comprehensive automated testing, integration and security testing, performance optimization, and scalable deployment. Implement HTTPS, encryption, secrets management, security headers, CSRF protection, audit logging, dependency vulnerability scanning, backup and recovery mechanisms, and monitoring. Establish CI/CD workflows, GDPR-aligned privacy safeguards, data retention and deletion policies, and ongoing security maintenance.

## Known Limitations

The application is currently under active development and is not yet suitable for production deployment. The following limitations are being addressed throughout the development roadmap.

- **Authentication and Authorization:** The existing AI Interviewer API does not enforce authentication or role-based access control. Secure administrator authentication, passwordless candidate access, and protected endpoints are planned.

- **Application Integration:** AI Interviewer and InterviewHub currently operate as separate components. A unified frontend, secure inter-service communication, and centralized interview management have not yet been implemented.

- **Data Persistence and Management:** The AI engine stores interviews in JSON files, while InterviewHub uses PostgreSQL. Centralized interview tracking, database-backed session management, and appropriate data retention and deletion mechanisms are planned.

- **Candidate Verification and Abuse Prevention:** Email uniqueness does not establish candidate identity or prevent automated registrations. Email verification, bot protection, rate limiting, secure session handling, and single-attempt enforcement are still under development.

- **AI Reliability and Security:** The local LLM may produce repetitive, inconsistent, or unsupported evaluations. Answer-reference validation ensures that cited responses exist but does not guarantee the accuracy of AI-generated conclusions. Further improvements will address evaluation consistency, prompt injection, output validation, and model reliability.

- **Privacy and Data Protection:** Comprehensive access controls, encryption, audit logging, data retention policies, and GDPR-aligned personal data management have not yet been implemented. Real candidate information should not be processed until the necessary protections are established.

- **Recruitment Assessment and Fairness:** AI-generated assessments have not been validated for real-world employment decisions. Future evaluation tools will require job-related criteria, bias testing, explainable observations, human oversight, and appropriate regulatory compliance. The system must not autonomously make hiring or rejection decisions.

- **Production Readiness:** Automated security testing, CI/CD pipelines, monitoring, backup and recovery procedures, and production deployment safeguards are still planned. The current implementation is intended for local development, experimentation, and testing.

## Development Workflow

Work is currently organized on feature branches, with commits and pushes at tested milestones. The InterviewHub foundation is being developed on `feature/interview-hub-setup`; changes will be merged into `main` when integration is appropriate.

The README will be updated alongside meaningful changes so the distinction between **implemented**, **in progress**, and **planned** features stays accurate.

---

*Originally developed as a Mini AI Interviewer assignment; now expanding into InterviewHub, a unified AI-assisted recruitment platform.*
