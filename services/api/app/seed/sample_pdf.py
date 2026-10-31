"""Generate a synthetic lab report PDF for the document-upload demo.

Usage: python -m app.seed.sample_pdf <output.pdf>
"""
import sys
from datetime import date, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROWS = [
    ("Alanine Aminotransferase (ALT/SGPT)", "58", "U/L", "7 - 40", "H"),
    ("Aspartate Aminotransferase (AST/SGOT)", "41", "U/L", "10 - 40", "H"),
    ("Gamma-Glutamyl Transferase (GGT)", "64", "U/L", "8 - 61", "H"),
    ("Albumin", "4.3", "g/dL", "3.5 - 5.2", ""),
    ("Platelet Count", "226", "x10^3/uL", "150 - 400", ""),
    ("Hemoglobin A1c", "6.5", "%", "4.0 - 5.6", "H"),
    ("Glucose, Fasting", "118", "mg/dL", "70 - 99", "H"),
]


def build(path: str) -> None:
    collected = date.today() - timedelta(days=3)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=48, leftMargin=48, rightMargin=48)
    head = Table(
        [["NORTHSIDE DIAGNOSTICS (DEMO LAB)", "SYNTHETIC REPORT - NOT REAL PATIENT DATA"],
         ["Patient: MILLER, JOHN", f"Collected: {collected.isoformat()}"],
         ["DOB: 1978-09-21   Sex: M", f"Reported: {(collected + timedelta(days=1)).isoformat()}"],
         ["Ordering: Dr. Anika Patel, LiverWell Clinic", "Accession: ND-2026-448812"]],
        colWidths=[290, 230],
    )
    head.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10), ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                              ("TEXTCOLOR", (1, 0), (1, 0), colors.red), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    table = Table([["Test", "Result", "Units", "Reference range", "Flag"], *ROWS], colWidths=[220, 60, 70, 110, 40])
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9), ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7e6e2")), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.grey),
        ("TEXTCOLOR", (4, 1), (4, -1), colors.red), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    doc.build([head, Spacer(1, 18), Paragraph("<b>Comprehensive Metabolic &amp; Hepatic Panel</b>", styles["Heading4"]), table,
               Spacer(1, 18), Paragraph("H = above reference range. This document was generated for a software demonstration.", styles["Italic"])])


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "sample-lab-report.pdf")
