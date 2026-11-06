"""
Generates authentic government policy guideline PDFs for the schemes.
Uses ReportLab to create well-structured documents with headings, sections, and metadata.
"""

import os
import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

DATA_DIR = Path(__file__).resolve().parent
RAW_DOCS_DIR = DATA_DIR / "raw_documents"
CENTRAL_DOCS_DIR = RAW_DOCS_DIR / "central_schemes"
KARNATAKA_DOCS_DIR = RAW_DOCS_DIR / "karnataka_schemes"

for d in [RAW_DOCS_DIR, CENTRAL_DOCS_DIR, KARNATAKA_DOCS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def create_scheme_pdf(scheme: dict):
    filename = scheme.get("source_document_name")
    if not filename:
        filename = f"{scheme['id']}.pdf"
    
    level = scheme.get("level", "Central")
    sub_dir = KARNATAKA_DOCS_DIR if level == "Karnataka" else CENTRAL_DOCS_DIR
    file_path = sub_dir / filename
    root_path = RAW_DOCS_DIR / filename
    
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'GovTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1A365D"),
        alignment=1,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'GovSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#2B6CB0"),
        alignment=1,
        spaceAfter=15
    )
    h2_style = ParagraphStyle(
        'GovH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2C5282"),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'GovBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        'GovBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1A202C"),
        leftIndent=15,
        spaceAfter=3
    )

    story = []

    # Header / Emblem title
    level_tag = "GOVERNMENT OF INDIA" if scheme.get("level") == "Central" else "GOVERNMENT OF KARNATAKA"
    story.append(Paragraph(f"<b>OFFICIAL POLICY GUIDELINES & DIRECTIVE</b>", subtitle_style))
    story.append(Paragraph(f"{level_tag} &mdash; {scheme.get('department', 'Welfare Dept').upper()}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1A365D"), spaceAfter=10))

    # Scheme Title
    story.append(Paragraph(scheme["name"], title_style))
    story.append(Paragraph(f"Category: {scheme.get('category')} | Jurisdiction: {scheme.get('level')} | Date of Verification: {scheme.get('verification_date')}", subtitle_style))
    story.append(Spacer(1, 8))

    # 1. Scheme Overview
    story.append(Paragraph("1. OBJECTIVE AND SCOPE OF THE SCHEME", h2_style))
    story.append(Paragraph(scheme["description"], body_style))
    story.append(Spacer(1, 4))

    # 2. Financial Benefits & Assistance
    story.append(Paragraph("2. QUANTUM OF ASSISTANCE AND FINANCIAL BENEFITS", h2_style))
    story.append(Paragraph(f"<b>Core Benefit:</b> {scheme['benefits_summary']}", body_style))
    if scheme.get("financial_amount"):
        story.append(Paragraph(f"<b>Sanctioned Scale of Assistance:</b> {scheme['financial_amount']}", body_style))
    story.append(Spacer(1, 4))

    # 3. Comprehensive Eligibility Criteria
    story.append(Paragraph("3. STATUTORY ELIGIBILITY CONDITIONS & QUALIFICATIONS", h2_style))
    story.append(Paragraph(scheme["eligibility_summary"], body_style))
    
    # Specific criteria table
    crit_data = [
        ["Criterion", "Prescribed Parameter", "Verification Mode"],
        ["Age Range", f"{scheme.get('age_min', 0)} to {scheme.get('age_max', 100)} years", "Aadhaar / Birth Certificate"],
        ["State Domicile", scheme.get("state_residence", "All India"), "Domicile / Ration Card"],
        ["Annual Income Ceiling", f"Rs. {scheme['income_ceiling']:,.2f}" if scheme.get('income_ceiling') else "No strict ceiling / Category specific", "Income Certificate / Self-Declaration"],
        ["Eligible Occupations", ", ".join(scheme.get("target_occupations", ["All"])), "Proof of Occupation / Vending / Land"],
        ["Gender Coverage", ", ".join(scheme.get("target_genders", ["All"])), "Photo Identity Document"],
        ["Social Categories", ", ".join(scheme.get("target_categories", ["All"])), "Caste Certificate (if applicable)"]
    ]
    t = Table(crit_data, colWidths=[130, 240, 160])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    # 4. Mandatory Documents
    story.append(Paragraph("4. MANDATORY DOCUMENTATION CHECKLIST", h2_style))
    for doc_item in scheme.get("required_documents", []):
        story.append(Paragraph(f"&bull; <b>{doc_item}</b>", bullet_style))
    story.append(Spacer(1, 4))

    # 5. Application Procedure & Workflow
    story.append(Paragraph("5. STEP-BY-STEP APPLICATION PROCEDURE", h2_style))
    for step in scheme.get("application_steps", []):
        story.append(Paragraph(step, bullet_style))
    story.append(Spacer(1, 4))

    # 6. Official Portal & Authority
    story.append(Paragraph("6. OFFICIAL APPLICATION PORTAL & LEGAL NOTICE", h2_style))
    story.append(Paragraph(f"<b>Designated Official Portal:</b> <font color='#2B6CB0'><u>{scheme.get('application_portal')}</u></font>", body_style))
    story.append(Paragraph(f"<b>Application Deadline:</b> {scheme.get('deadline', 'Open continuous enrollment')}", body_style))
    story.append(Paragraph(f"<b>Source Directive:</b> {scheme.get('source_url')}", body_style))
    story.append(Spacer(1, 6))

    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#A0AEC0"), spaceAfter=6))
    story.append(Paragraph("<i>Notice: This official document is indexed for citizen awareness under the Right to Information and public welfare guidelines. Citizens are advised not to entertain fraudulent intermediaries. Direct Benefit Transfers are made exclusively to bank accounts seeded with Aadhaar.</i>", ParagraphStyle('Note', parent=styles['Italic'], fontSize=8, leading=11, textColor=colors.HexColor("#718096"))))

    doc.build(story)
    # Also save a copy in root RAW_DOCS_DIR for direct lookup
    try:
        import shutil
        shutil.copy2(file_path, root_path)
    except Exception:
        pass
    print(f"Generated PDF: {file_path}")
    return str(file_path)


def generate_all_pdfs():
    seed_file = DATA_DIR / "seed_schemes.json"
    with open(seed_file, "r", encoding="utf-8") as f:
        schemes = json.load(f)
    
    generated = []
    for s in schemes:
        path = create_scheme_pdf(s)
        generated.append(path)
    print(f"Successfully generated {len(generated)} official scheme guideline PDFs.")


if __name__ == "__main__":
    generate_all_pdfs()
