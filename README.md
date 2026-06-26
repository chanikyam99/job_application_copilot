# Job Application Co-Pilot

Job Application Co-Pilot is a full-stack web application for tracking job applications and generating AI-assisted career artifacts such as fit analysis, resume rewrites, cover letters, and interview Q&A.

This document is written as a handoff guide for another agent. It is intended to provide enough context for someone to understand the system, make changes safely, and extend the product without breaking the current architecture.

## 1. What this project does

Users can:

- create an account and log in securely
- add job applications with a job title, company, job description, and resume upload
- view their applications in a dashboard
- generate AI-based content for each application
- update application status during the hiring process
- download a generated cover letter as a DOCX file

## 2. High-level architecture

The project is split into two main parts:

- Backend: a FastAPI service that handles authentication, database access, file processing, and AI orchestration
- Frontend: a lightweight static website built with HTML, CSS, and vanilla JavaScript

The app uses a simple request flow:

1. The user authenticates in the frontend.
2. The frontend calls the FastAPI backend through the API wrapper in [frontend/js/api.js](frontend/js/api.js).
3. The backend validates the user, persists data in SQLite, and optionally runs the AI pipeline.
4. Generated results are stored in the database and shown back in the UI.

## 3. Project structure

```text
backend/
  agents/
    orchestrator.py
  routers/
    applications_router.py
    auth_router.py
  utils/
    docx_generator.py
    pdf_parser.py
  auth.py
  database.py
  main.py
  models.py
  requirements.txt
  schemas.py

frontend/
  css/
  js/
  application.html
  dashboard.html
  index.html
  new-application.html
```

## 4. Backend map

### Core entry points

- [backend/main.py](backend/main.py): creates the FastAPI app, enables CORS, registers routers, and initializes the database tables.
- [backend/auth.py](backend/auth.py): handles JWT token creation, password hashing, password verification, and protected-route authentication.
- [backend/database.py](backend/database.py): sets up the SQLAlchemy engine, session factory, and database connection.

### Domain models

- [backend/models.py](backend/models.py): defines the SQLAlchemy models:
  - User
  - Application
  - Draft
  - ApplicationStatus

### API routers

- [backend/routers/auth_router.py](backend/routers/auth_router.py): signup, login, and profile endpoints.
- [backend/routers/applications_router.py](backend/routers/applications_router.py): application CRUD, generation, regeneration, status updates, and download logic.

### AI and utilities

- [backend/agents/orchestrator.py](backend/agents/orchestrator.py): runs the multi-agent pipeline for fit analysis, resume rewriting, cover letter generation, and interview Q&A.
- [backend/utils/pdf_parser.py](backend/utils/pdf_parser.py): extracts text from uploaded PDF resumes.
- [backend/utils/docx_generator.py](backend/utils/docx_generator.py): builds a DOCX file for the cover letter.

### Schemas and validation

- [backend/schemas.py](backend/schemas.py): defines request and response Pydantic models used by FastAPI.

## 5. Frontend map

- [frontend/index.html](frontend/index.html): login and signup experience.
- [frontend/dashboard.html](frontend/dashboard.html): main dashboard for listing applications.
- [frontend/new-application.html](frontend/new-application.html): form for creating a new application.
- [frontend/application.html](frontend/application.html): detailed view for one application and generated artifacts.
- [frontend/js/api.js](frontend/js/api.js): shared API layer for auth, fetch requests, loading state, toasts, and error handling.

## 6. Data model summary

The database is intentionally simple:

- User: one user has many applications.
- Application: stores the job title, company, job description, original resume text, status, and metadata.
- Draft: stores AI-generated outputs for one application, including fit analysis, resume rewrite, cover letter, and interview questions.

Important behavior:

- every application is scoped to the authenticated user
- generated content is stored as JSON text or plain text in the Draft record
- deleting an application cascades to its Draft entry

## 7. Authentication and security model

Authentication is currently implemented with JWTs:

- login returns a bearer token
- protected routes require the token in the Authorization header
- the backend loads the user from the database and rejects invalid or missing tokens

Security conventions to preserve:

- always filter application queries by the current user id
- never expose another user’s data
- do not return password hashes to the frontend
- keep token validation centralized in [backend/auth.py](backend/auth.py)

## 8. AI pipeline behavior

The AI workflow is orchestrated in [backend/agents/orchestrator.py](backend/agents/orchestrator.py).

Current flow:

1. fit analysis runs first
2. resume rewriting, cover letter writing, and interview Q&A run in parallel
3. the results are stored in the application’s Draft record

This means that if you add a new generated section, you will likely need to update:

- the orchestrator logic
- the Draft model fields
- the application generation endpoints
- the frontend UI that renders the new output

## 9. Important implementation conventions

These conventions are already present in the codebase and should be preserved unless a change explicitly requires otherwise:

- use FastAPI routers rather than putting all logic in one file
- keep database access inside dependency-injected session flow
- use Pydantic schemas for API request/response validation
- keep upload handling in the router layer, not in the frontend
- preserve the current user scoping on every application-related endpoint
- use async calls for AI requests so the API remains responsive
- keep static frontend assets simple and framework-free unless the project is intentionally migrated

## 10. How to make changes safely

### For backend changes

1. Understand the relevant router, schema, and model before editing.
2. If a new field is needed, update the model and the schema together.
3. If a new API endpoint is needed, add it to the correct router and keep authentication consistent.
4. If the change affects generated content, update the orchestrator and the Draft persistence logic.
5. Test the endpoint through the API and confirm the DB state is correct.

### For frontend changes

1. Read the relevant HTML page and the shared API helper first.
2. Keep UI behavior aligned with the backend endpoints.
3. Use the existing loading/toast helpers in [frontend/js/api.js](frontend/js/api.js) for consistency.
4. Prefer small changes that reuse the current structure rather than introducing a framework unnecessarily.

### For database changes

1. treat SQLite as the current default and do not assume Postgres
2. if schema changes become significant, add migration tooling later
3. avoid breaking existing model relationships unless the code and UI are updated together

## 11. Environment and setup

The backend reads configuration from [backend/.env](backend/.env).

Required values include:

```env
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=sqlite:///./job_copilot.db
```

### Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run the frontend

```bash
cd frontend
python -m http.server 8080
```

Then open:

- http://localhost:8080/index.html

## 12. Current limitations

- there is no automated test suite yet
- the frontend is intentionally minimal and static
- the app currently uses SQLite for local development
- resume uploads are limited to PDF files
- AI responses are dependent on the Groq API key and model availability

## 13. Good starting points for future work

Possible enhancements that fit the current architecture:

- add profile editing and password reset
- support DOCX or plain-text resume uploads
- add richer application analytics and filtering
- improve AI prompt tuning and structured output handling
- add deployment config for production hosting
- introduce a proper frontend framework if the UI grows significantly

## 14. Suggested reading order for a new agent

If another agent is taking over this project, the best reading order is:

1. [backend/main.py](backend/main.py)
2. [backend/auth.py](backend/auth.py)
3. [backend/models.py](backend/models.py)
4. [backend/routers/applications_router.py](backend/routers/applications_router.py)
5. [backend/agents/orchestrator.py](backend/agents/orchestrator.py)
6. [frontend/js/api.js](frontend/js/api.js)
7. [frontend/application.html](frontend/application.html)
8. [frontend/dashboard.html](frontend/dashboard.html)

That sequence gives the clearest path from request handling to data persistence to UI rendering.
