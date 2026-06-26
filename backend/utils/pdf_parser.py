from pypdf import PdfReader
import io
import re


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts plain text from PDF bytes.
    Returns the full text as a single string with page breaks as newlines.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    return "\n".join(pages_text).strip()


def parse_resume_sections(text: str) -> dict:
    """
    Best-effort heuristic to split resume into named sections.
    Resumes have no standard format, so this is approximate.

    Used only for the upload preview in new-application.html.
    The LLM agents receive the full text regardless.
    """
    sections = {
        "header":     [],
        "summary":    [],
        "experience": [],
        "education":  [],
        "skills":     [],
        "other":      [],
    }

    section_keywords = {
        "summary":    ["summary", "objective", "profile", "about me"],
        "experience": ["experience", "work history", "employment", "professional background"],
        "education":  ["education", "academic", "qualification", "degree"],
        "skills":     ["skills", "technical skills", "competencies", "technologies"],
    }

    current_section = "header"

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # Check if this line is a section header:
        # short (under 60 chars) AND matches a known keyword
        if len(stripped) < 60:
            line_lower = stripped.lower()
            matched = False
            for section_name, keywords in section_keywords.items():
                if any(kw in line_lower for kw in keywords):
                    current_section = section_name
                    matched = True
                    break
            if matched:
                continue

        sections[current_section].append(stripped)

    return {k: "\n".join(v) for k, v in sections.items()}