import asyncio
import json
import os
# REMOVED: from unittest import result  — was an unused import left from debugging
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

# AsyncGroq: the async version of the Groq client.
# WHY async? Sync Groq inside an async FastAPI endpoint blocks the event loop
# for 15 seconds — no other requests can be handled during that time.
# AsyncGroq releases the loop while waiting, so FastAPI stays responsive.
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"  # Best free-tier model on Groq


def _safe_parse_json(content: str, fallback=None):
    """
    Parses JSON from LLM output safely.
    LLMs sometimes wrap JSON in markdown code blocks (```json ... ```)
    or add explanatory text before/after. This handles all those cases.
    """
    # Direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Strip markdown code blocks
    for marker in ["```json", "```"]:
        if marker in content:
            start = content.find(marker) + len(marker)
            end   = content.rfind("```")
            if end > start:
                try:
                    return json.loads(content[start:end].strip())
                except json.JSONDecodeError:
                    pass

    # Find outermost { } or [ ]
    for open_c, close_c in [('{', '}'), ('[', ']')]:
        start = content.find(open_c)
        end   = content.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass

    return fallback if fallback is not None else {}


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 1: FIT ANALYST
# Runs FIRST. Its output feeds agents 2, 3, and 4.
# ─────────────────────────────────────────────────────────────────────────────

async def run_fit_analyst(resume_text: str, jd_text: str) -> dict:
    """
    Analyzes how well the resume matches the job description.

    Temperature 0.2: Very low creativity. We need consistent, structured JSON.
    A higher temp here would produce inconsistent match scores across regenerations.
    """
    prompt = f"""You are an expert ATS system and career coach.

Analyze how well this resume matches the job description.

RESUME:
{resume_text[:3500]}

JOB DESCRIPTION:
{jd_text[:3000]}

Return ONLY a valid JSON object — no markdown, no explanation before or after:
{{
  "match_score": <integer 0-100>,
  "matching_requirements": ["<req 1>", "<req 2>", ...],
  "missing_requirements": ["<gap 1>", ...],
  "skills_to_emphasize": ["<skill 1>", ...],
  "key_keywords": ["<keyword 1>", ...],
  "overall_summary": "<2-3 sentences on fit>"
}}"""

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1500,
    )

    return _safe_parse_json(
        response.choices[0].message.content,
        fallback={
            "match_score": 0,
            "matching_requirements": [],
            "missing_requirements": [],
            "skills_to_emphasize": [],
            "key_keywords": [],
            "overall_summary": "Analysis failed — please regenerate."
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 2: RESUME WRITER
# Gets fit_analysis as context. Rewrites bullets with JD keywords.
# ─────────────────────────────────────────────────────────────────────────────

async def run_resume_writer(resume_text: str, jd_text: str, fit_analysis: dict) -> dict:
    """
    Rewrites resume bullets to be more impactful and keyword-optimized.

    Temperature 0.4: Slightly creative for varied action verbs and phrasing.
    Too low = repetitive sentence structure. Too high = hallucinated achievements.

    WHY pass fit_analysis? Without it, the LLM guesses what to emphasize.
    With it, it knows exactly which keywords to weave in and which gaps to address.
    """
    keywords  = ", ".join(fit_analysis.get("key_keywords", [])[:10])
    emphasize = ", ".join(fit_analysis.get("skills_to_emphasize", [])[:5])
    missing   = ", ".join(fit_analysis.get("missing_requirements", [])[:3])

    prompt = f"""You are an expert resume writer specializing in ATS optimization.

ORIGINAL RESUME:
{resume_text[:3500]}

TARGET JOB DESCRIPTION:
{jd_text[:2500]}

OPTIMIZATION GUIDE (from fit analysis):
- Keywords to include naturally: {keywords}
- Experiences to emphasize: {emphasize}
- Gaps to address diplomatically if possible: {missing}

RULES:
1. Use strong action verbs (Led, Architected, Drove, Reduced, Increased, Delivered, Designed)
2. Add quantification where original is vague ("improved performance" → "reduced API latency by 40%")
3. Weave JD keywords in naturally — do NOT keyword-stuff
4. Do NOT invent jobs, companies, or metrics that aren't in the original resume
5. Keep all jobs, dates, education intact — only improve the bullet wording

Return ONLY valid JSON (no markdown):
{{
  "rewritten_resume": "<full rewritten resume as plain text>",
  "changes": [
    {{
      "original":  "<exact original bullet>",
      "rewritten": "<improved version>",
      "reason":    "<one sentence: why this helps>"
    }}
  ]
}}"""

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=4000,
    )

    # result = _safe_parse_json(response.choices[0].message.content, fallback={})
    # print(type(result))
    # print(result)
    # return {
    #     "rewritten_resume": result.get("rewritten_resume", resume_text),
    #     "changes": result.get("changes", [])
    # }
    result = _safe_parse_json(
        response.choices[0].message.content,
        fallback={}
    )

    # Model returned only a list of changes
    if isinstance(result, list):
        return {
            "rewritten_resume": resume_text,
            "changes": result
        }

    # Model returned expected structure
    if isinstance(result, dict):
        return {
            "rewritten_resume": result.get("rewritten_resume", resume_text),
            "changes": result.get("changes", [])
        }

    # Fallback
    return {
        "rewritten_resume": resume_text,
        "changes": []
    }


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 3: COVER LETTER WRITER
# Gets fit_analysis as context. Writes a targeted 1-page cover letter.
# ─────────────────────────────────────────────────────────────────────────────

async def run_cover_letter_writer(
    resume_text: str,
    jd_text: str,
    fit_analysis: dict,
    job_title: str,
    company: str
) -> str:
    """
    Writes a tailored cover letter.

    Temperature 0.65: Cover letters need personality and varied sentence structure.
    0.2 would produce stiff, robotic-sounding letters.
    0.65 hits the sweet spot: professional but human-sounding.

    Returns plain text (not JSON) — cover letters are flowing prose,
    not structured data.
    """
    matching = ", ".join(fit_analysis.get("matching_requirements", [])[:4])
    score    = fit_analysis.get("match_score", 70)

    prompt = f"""You are an expert cover letter writer.

CANDIDATE RESUME:
{resume_text[:2500]}

JOB: {job_title} at {company}

JOB DESCRIPTION:
{jd_text[:2000]}

CANDIDATE'S STRONGEST MATCHING POINTS: {matching}
(Overall fit score: {score}/100)

Write a compelling, personalized cover letter. Rules:
1. Do NOT start with "I am writing to apply for..." — boring. Use a strong opening hook.
2. Para 1 (hook + fit): Why excited about this specific role and your top credential
3. Para 2 (proof): 2 specific achievements from resume that address JD requirements
4. Para 3 (company connection): Show you know what this company does/values — researched tone
5. Para 4 (close): Confident call to action — not desperate, not arrogant
6. Under 400 words total
7. Professional but warm — not corporate-speak

Return ONLY the cover letter text. No JSON, no "Here is your cover letter:", nothing extra."""

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.65,
        max_tokens=1200,
    )

    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 4: INTERVIEWER
# Gets fit_analysis as context. Generates targeted Q&A pairs.
# ─────────────────────────────────────────────────────────────────────────────

async def run_interviewer(resume_text: str, jd_text: str, fit_analysis: dict) -> list:
    """
    Generates 10 interview questions with answers grounded in the resume.

    Temperature 0.5: Balance creativity (varied questions) with accuracy
    (answers must reference real resume content, not be invented).

    The mix of question types maps to real interview structures:
    - Behavioral (STAR): Asked in 90% of interviews
    - Technical: Validates domain skills
    - Situational: Reveals judgment and decision-making
    - Weakness/gap: Addresses the missing requirements diplomatically
    """
    missing  = ", ".join(fit_analysis.get("missing_requirements", [])[:3])
    keywords = ", ".join(fit_analysis.get("key_keywords", [])[:5])

    prompt = f"""You are a senior hiring manager and interview coach.

CANDIDATE RESUME:
{resume_text[:2500]}

JOB DESCRIPTION:
{jd_text[:2000]}

CANDIDATE'S POTENTIAL WEAK SPOTS (prepare for these): {missing}
KEY TECHNICAL AREAS TO COVER: {keywords}

Generate exactly 10 interview questions. Mix:
- 3 behavioral (STAR: Situation, Task, Action, Result)
- 3 technical/domain (testing skills in the JD)
- 2 situational ("How would you handle X?")
- 2 weakness/gap (diplomatically address missing requirements)

For each question, give a strong sample answer grounded in the ACTUAL resume.

Return ONLY a valid JSON array (no markdown):
[
  {{
    "type": "behavioral",
    "question": "<the interview question>",
    "sample_answer": "<3-5 sentence STAR answer grounded in the resume>",
    "tip": "<one coaching tip for this question type>"
  }}
]"""

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=4000,
    )

    result = _safe_parse_json(response.choices[0].message.content, fallback=[])
    return result if isinstance(result, list) else []


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR: the function called by the API endpoint
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(
    resume_text: str,
    jd_text: str,
    job_title: str,
    company: str
) -> dict:
    """
    Runs the full multi-agent pipeline.

    Step 1: Fit analysis — sequential (others depend on its output)
    Step 2: Resume writer + Cover letter + Interviewer — PARALLEL

    asyncio.gather() starts all 3 simultaneously.
    Wall-clock ≈ max(agent2, agent3, agent4) ≈ 15s vs 45s sequential.
    """
    # Step 1: SEQUENTIAL — must finish before step 2
    fit_analysis = await run_fit_analyst(resume_text, jd_text)

    # Step 2: PARALLEL — all 3 run simultaneously
    resume_result, cover_letter, interview_qa = await asyncio.gather(
        run_resume_writer(resume_text, jd_text, fit_analysis),
        run_cover_letter_writer(resume_text, jd_text, fit_analysis, job_title, company),
        run_interviewer(resume_text, jd_text, fit_analysis),
    )

    return {
        "fit_analysis":   fit_analysis,
        "resume_rewrite": resume_result.get("rewritten_resume", ""),
        "resume_changes": resume_result.get("changes", []),
        "cover_letter":   cover_letter,
        "interview_qa":   interview_qa,
    }