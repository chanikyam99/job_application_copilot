# Job Application Co-Pilot

Job Application Co-Pilot is a full-stack web app for tracking job applications and generating AI-assisted career assets such as fit analysis, tailored resume rewrites, cover letters, and mock interview question packs.

## What the app does

Users can:

- create an account and log in securely
- upload a resume PDF and add a job title, company, and job description
- create a new application entry and generate an AI-powered "kit"
- review fit analysis, rewritten resume content, cover letter text, and interview Q&A
- update application status throughout the hiring process
- download generated cover letters and rewritten resumes as DOCX files

## Tech stack

- Backend: FastAPI, SQLAlchemy, JWT auth, Pydantic
- Frontend: static HTML, CSS, and vanilla JavaScript
- Database: SQLite for local development, PostgreSQL in production
- AI: Groq API via the asynchronous Groq client
- File handling: PDF parsing with pypdf and DOCX generation with python-docx

## Project structure

```text
backend/
  agents/orchestrator.py
  routers/auth_router.py
  routers/applications_router.py
  utils/pdf_parser.py
  utils/docx_generator.py
  auth.py
  database.py
  main.py
  models.py
  schemas.py
  requirements.txt

frontend/
  index.html
  dashboard.html
  new-application.html
  application.html
  css/main.css
  js/api.js
  js/config.js
```

## Getting started

### 1. Local backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # On Windows use .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Update the values in [backend/.env](backend/.env) with your own settings:

```env
SECRET_KEY=change-this-to-a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
GROQ_API_KEY=your-groq-api-key
DATABASE_URL=sqlite:///./job_copilot.db
ALLOWED_ORIGINS=*
```

Start the backend:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API docs will be available at http://localhost:8000/docs.

### 2. Local frontend setup

```bash
cd frontend
python -m http.server 8080
```

Then open http://localhost:8080/index.html.

## Production deployment

This project is designed to run with:

- Render for the FastAPI backend
- Vercel for the static frontend
- PostgreSQL for the production database

### Backend on Render

- Connect the [backend](backend) folder to a Render web service.
- Use the following build/start settings:
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Set these environment variables in Render:

```env
SECRET_KEY=your-production-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
GROQ_API_KEY=your-groq-api-key
DATABASE_URL=postgresql://user:password@host:5432/dbname
ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
```

Render will automatically run the FastAPI app from [backend/main.py](backend/main.py).

### Frontend on Vercel

- Deploy the [frontend](frontend) folder as a static site.
- No build step is required for the current vanilla HTML/CSS/JS setup.
- If your Render backend uses a different URL than the default one, update [frontend/js/config.js](frontend/js/config.js) or set the frontend to use a custom backend URL before the app loads.

### Database on PostgreSQL

- Use a managed PostgreSQL database such as Render Postgres.
- Set the `DATABASE_URL` environment variable on the Render backend service to your PostgreSQL connection string.
- The app uses SQLAlchemy models in [backend/models.py](backend/models.py), so the schema is created automatically when the backend starts.

## Current workflow

1. Sign up or log in.
2. Create a new application with a PDF resume, job title, company, and job description.
3. Open the application detail page and click Generate Kit.
4. The backend runs a multi-agent pipeline that produces:
   - fit analysis
   - resume rewrite with change highlights
   - cover letter
   - interview Q&A
5. Download the generated assets or regenerate a single section if needed.

## Main API endpoints

- POST /auth/signup
- POST /auth/login
- GET /auth/me
- GET /applications
- POST /applications
- POST /applications/{id}/generate
- GET /applications/{id}
- POST /applications/{id}/regenerate/{section}
- PATCH /applications/{id}/status
- GET /applications/{id}/download/cover-letter
- GET /applications/{id}/download/resume
- DELETE /applications/{id}

## Notes

- SQLite is the default for local development, while PostgreSQL is recommended for Render production.
- Resume uploads are limited to PDF files.
- AI-generated content depends on a valid Groq API key.
- There is no automated test suite yet, so manual verification via the UI and API is still the main validation path.
