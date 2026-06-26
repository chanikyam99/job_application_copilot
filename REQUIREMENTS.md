# Job Application Co-Pilot — Requirements

> **Module 6 · IITR-SE-2509-COHORT-B · Project 02: Career & Personal Branding**
> Kickoff: Fri 5 Jun 2026 · Final Submission: Sun 28 Jun 2026

---

## Problem Statement

Applying for jobs is a grind: read the JD, re-read your resume, tweak bullet points for relevance, write a fresh cover letter, prepare for likely interview questions. Every role gets ~20 minutes of effort because that's all anyone has. AI can take the grind out — turn "20 minutes of tired tweaking" into "10 minutes of reviewing four high-quality drafts."

---

## General Capstone Rules

- Solo build — no teams
- Must have real backend code, a real database, and a working frontend
- Free / very-low-cost tools only:
  - LLMs: OpenAI / Groq / Hugging Face free tiers, Ollama locally, or Gemini Flash
  - Deployment: Render / Railway free tier
- Do not use any tool not taught in class unless a linked reference doc is provided inside the project

---

## Core Outcomes (Must Have)

All of the following must be implemented for a complete submission:

1. **Resume Upload** — user uploads their resume as a PDF
2. **Job Description Input** — user pastes a JD as text or a URL
3. **Multi-agent pipeline** producing four artifacts:
   - **Fit Analysis** — which JD requirements the user meets, which they don't, and what to emphasise
   - **Tailored Resume Rewrite** — same role list, sharper bullets, JD keywords woven in
   - **Cover Letter Draft** — 1 page, tone-matched to the company
   - **Mock Interview Question Pack** — 10 likely questions + sample answers grounded in the user's resume
4. **Artifact Persistence** — all four artifacts saved per "role application" entry so the user can manage a pipeline of roles applied for
5. **Diff View** — see resume bullet "before" and "after" side by side

---

## Suggested Tech Stack

### Frontend
- **Primary:** Vanilla HTML + CSS + JS
  - This is a CRUD app (multiple roles, drafts, diffs); use `fetch()` to call FastAPI
  - Requires CORS setup on the backend — see `ref-fastapi-cors-fetch.pdf`
- **Alternative:** Streamlit (simpler, but multi-page navigation is clunky)

### Backend / AI Core
- **FastAPI** with JWT authentication
- **Multi-agent pipeline:**
  - orchestrator → fit-analyst → resume-writer → cover-letter-writer → interviewer
  - Implement with **LangGraph supervisor pattern** (M6) or hand-rolled coordinator (M5)
- **LLM:** Groq `llama-3.3-70b-versatile` (fast, free) or OpenAI `gpt-4o-mini`

### Storage
- **SQLite + SQLAlchemy** for relational data
  - Tables: `users`, `roles` (job_title, company, jd_text), `drafts` (resume_rewrite, cover_letter, interview_qa), `revisions`
- **Resume PDF parsing:** `pypdf`

---

## Agent Pipeline — Pseudo-Workflow

```
Upload resume PDF + JD (text or URL) → FastAPI /applications · JWT
                        ↓
Parse PDF → resume sections → If URL: scrape JD → Save original_resume + jd_text
                        ↓
          Orchestrator → Agent 1: Fit analysis (LLM)
                        ↓
            ┌── fit_analysis feeds the parallel stage ──┐
            │                                           │
  Agent 2: Resume rewrite   Agent 3: Cover letter   Agent 4: Interview Q&A
            └───────────────────────┬───────────────────┘
                                    ↓
  Collect outputs → persist (original + drafts) → Frontend: 4 artifacts + diff view
```

---

## Sample Features to Build

| Feature | Details |
|---|---|
| Resume upload + PDF parsing | Parse into structured sections: header, experience, education, skills |
| JD input | Paste box for raw text; bonus: paste a LinkedIn URL and scrape with `requests` + `beautifulsoup4` |
| Roles list view | Every application prepped, with status: `applied / not yet / rejected / interviewed` |
| Diff view | Old bullet text struck out, new text in green |
| Regenerate section buttons | Re-run a single agent without rerunning the full pipeline |
| Download buttons | Cover letter as `.docx` (use `python-docx`), resume as PDF |

---

## Open-Ended Stretch Goals

These are optional extensions. Start experimenting here once core outcomes are complete.

- **ATS Scorer** — second LLM pass scoring the rewritten resume against the JD on keyword density
- **Voice Mock Interview** — use browser speech-to-text for the user's answer; LLM grades it and gives feedback
- **Salary Negotiation Coach** — give the role + the offer, get scripts for negotiation
- **Calendar Integration** — schedule follow-up reminders 1 week after applying
- **Deployment** — deploy using `ref-deploy-render-railway.pdf`

---

## API Endpoints (Suggested)

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/signup` | Register a new user |
| POST | `/auth/login` | Login, receive JWT |
| POST | `/applications` | Create new role application (upload resume PDF + JD) |
| GET | `/applications` | List all role applications for logged-in user |
| GET | `/applications/{id}` | Get a specific application with all drafts |
| POST | `/applications/{id}/regenerate/{section}` | Re-run one agent (fit / resume / cover / interview) |
| PATCH | `/applications/{id}/status` | Update application status |

---

## Database Schema

### `users`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| email | TEXT UNIQUE | |
| hashed_password | TEXT | |
| created_at | DATETIME | |

### `roles`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK → users | |
| job_title | TEXT | |
| company | TEXT | |
| jd_text | TEXT | |
| original_resume | TEXT | parsed resume text |
| status | TEXT | `not_yet / applied / rejected / interviewed` |
| created_at | DATETIME | |

### `drafts`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| role_id | INTEGER FK → roles | |
| fit_analysis | TEXT | JSON or plain text |
| resume_rewrite | TEXT | |
| cover_letter | TEXT | |
| interview_qa | TEXT | JSON array of Q+A pairs |
| created_at | DATETIME | |

### `revisions`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| draft_id | INTEGER FK → drafts | |
| section | TEXT | which section was regenerated |
| content | TEXT | new content |
| created_at | DATETIME | |

---

## Reference Material

| File | When to use |
|---|---|
| `ref-fastapi-cors-fetch.pdf` | **Required** — vanilla JS frontend calling FastAPI needs CORS |
| `ref-langgraph-llm-wiring.pdf` | Only if using LangGraph for the multi-agent pipeline |
| `ref-openai-native-tools.pdf` | Only if any agent needs native function-calling (e.g., LinkedIn scrape tool) |
| `ref-deploy-render-railway.pdf` | For the deployment stretch goal |

Everything else is covered in M3 (FastAPI + JWT + CRUD), M4 (LLMs + embeddings), M5 (multi-agent), and M6 (LangGraph) sessions.

---

## Deliverables Checklist

### Code / App
- [ ] Working frontend (Vanilla HTML+JS or Streamlit)
- [ ] FastAPI backend with JWT auth
- [ ] SQLite database with correct schema
- [ ] Multi-agent pipeline (4 agents minimum)
- [ ] All 4 artifacts generated and displayed
- [ ] Diff view for resume bullets
- [ ] Per-role artifact persistence
- [ ] Role status management (not yet / applied / rejected / interviewed)

### Submission Package
- [ ] **Project Video** — screen recording of the working app, under 5 minutes (Loom / OBS / any recorder)
- [ ] **Presentation** — slides covering: problem, who it's for, architecture diagram, what works, what's next, what you'd build with 2 more weeks (Gamma / Canva / Google Slides)
- [ ] **Frontend** — public deployed URL (Streamlit Cloud / Render / Vercel) OR GitHub repo with clear README for local run
- [ ] **Backend** — public FastAPI URL + working `/docs` Swagger link OR GitHub repo with `requirements.txt`, `.env.example`, and Alembic migrations folder (if used)
- [ ] **Database schema** — DBdiagram / dbml / hand-drawn diagram OR `models.py` linked from README
- [ ] **Frontend mockups** *(optional)* — Figma / Stitch / sketches used during building

### Key Dates
| Date | Milestone |
|---|---|
| Fri 5 Jun 2026 | Kickoff — lock project choice via Google Form |
| Every week | TA doubt-resolution session — bring blockers, code, screenshots |
| Sun 28 Jun 2026 EOD | Final submission deadline (LMS assignment) |
