from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io


def generate_cover_letter_docx(cover_letter_text: str, job_title: str, company: str) -> bytes:
    """
    Generates a formatted .docx cover letter.
    Returns bytes so FastAPI can stream it as a file download.
    """
    doc = Document()

    # Standard professional margins
    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.25)
        section.right_margin  = Inches(1.25)

    # Heading
    title_para = doc.add_heading(level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_para.add_run("Cover Letter")
    run.font.size      = Pt(16)
    run.font.color.rgb = RGBColor(0x1e, 0x40, 0xaf)  # dark blue

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = subtitle.add_run(f"{job_title}  ·  {company}")
    sub_run.font.size      = Pt(11)
    sub_run.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

    doc.add_paragraph()  # blank line spacer

    # Body — split on double newlines (paragraph breaks)
    paragraphs = [p.strip() for p in cover_letter_text.split("\n\n") if p.strip()]
    for para_text in paragraphs:
        para = doc.add_paragraph()
        run  = para.add_run(para_text)
        run.font.size                       = Pt(11)
        para.paragraph_format.space_after   = Pt(10)
        para.paragraph_format.line_spacing  = Pt(14)

    # Save to in-memory bytes buffer
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()