"""
PDF report generator.
- generate_report()         : per-session, one page per student showing Q1-40 correct/wrong
- generate_summary_report() : all students across all sessions, section scores table
"""
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, HRFlowable,
)

C_HEADER = colors.HexColor("#2c3e50")
C_GREEN  = colors.HexColor("#27ae60")
C_RED    = colors.HexColor("#e74c3c")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_WHITE  = colors.white
C_YELLOW = colors.HexColor("#f39c12")

SECTION_LABELS = ["Intelligence /10", "Science /10", "Social Science /10", "Mathematics /10"]
SECTION_KEYS   = ["intelligence", "science", "social", "math"]


def _base_style():
    return [
        ("BACKGROUND",    (0, 0), (-1, 0), C_HEADER),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.gray),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]


def _style():
    ss = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=ss["Title"],   textColor=C_HEADER, fontSize=16, spaceAfter=4)
    h2    = ParagraphStyle("H", parent=ss["Heading2"],textColor=C_HEADER, fontSize=12, spaceAfter=4)
    body  = ParagraphStyle("B", parent=ss["Normal"],  fontSize=9,  spaceAfter=2)
    small = ParagraphStyle("S", parent=ss["Normal"],  fontSize=7,  textColor=colors.gray)
    return title, h2, body, small


def generate_report(session_id: str, answer_key: dict,
                    sheets: List[Dict[str, Any]], output_path: str):
    """Per-session PDF: one page per student showing all 40 questions."""
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm,  bottomMargin=1.5*cm)
    title_s, h2_s, body_s, small_s = _style()
    story = []

    # Cover
    story.append(Paragraph("OMR Evaluation Report", title_s))
    story.append(Paragraph(f"Session: {session_id[:8]}  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", small_s))
    story.append(Paragraph(f"Total sheets: {len(sheets)}", body_s))
    story.append(Spacer(1, 0.5*cm))

    # Answer key summary on cover
    ak_rows = [["Q", "Ans"] * 5]
    for r in range(8):
        row = []
        for c in range(5):
            q = r + c * 8 + 1
            row += [str(q), answer_key.get(f"q{q}", "?") if q <= 40 else ""]
        ak_rows.append(row)
    ak_t = Table(ak_rows, colWidths=[1.0*cm, 1.0*cm]*5)
    ak_t.setStyle(TableStyle(_base_style()))
    story.append(Paragraph("Answer Key", h2_s))
    story.append(ak_t)
    story.append(PageBreak())

    # One page per student
    for sheet in sheets:
        detection = sheet.get("detection", {})
        questions = detection.get("questions", [])
        section_scores = detection.get("section_scores", {})
        student_id = detection.get("student_id", sheet.get("student_id", "Unknown"))
        total = detection.get("total_score", 0)

        story.append(Paragraph(f"Student: {student_id}", title_s))
        story.append(Paragraph(f"File: {sheet.get('filename', '')}  |  Total: {total}/40", body_s))
        story.append(HRFlowable(width="100%", thickness=1, color=C_HEADER, spaceAfter=6))

        if not questions:
            story.append(Paragraph(f"Error: {sheet.get('error', 'No data')}", body_s))
            story.append(PageBreak())
            continue

        # Q table split left/right
        headers = ["Q", "Marked", "Correct", ""]
        left  = [headers] + _q_rows(questions, 1, 20,  answer_key)
        right = [headers] + _q_rows(questions, 21, 40, answer_key)

        cw = [0.8*cm, 1.8*cm, 1.8*cm, 0.8*cm]
        lt = Table(left,  colWidths=cw)
        rt = Table(right, colWidths=cw)

        for t, rows in [(lt, left), (rt, right)]:
            ts = TableStyle(_base_style())
            for i, row in enumerate(rows[1:], 1):
                if row[3] == "✓":
                    ts.add("TEXTCOLOR", (3, i), (3, i), C_GREEN)
                    ts.add("BACKGROUND", (0, i), (-1, i), colors.HexColor("#d4edda"))
                else:
                    ts.add("TEXTCOLOR", (3, i), (3, i), C_RED)
                    ts.add("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8d7da"))
            t.setStyle(ts)

        combined = Table([[lt, Spacer(0.5*cm, 0), rt]])
        combined.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
        story.append(combined)
        story.append(Spacer(1, 0.4*cm))

        # Section scores
        sec_rows = [["Section", "Score", "Out of"]]
        for key, label in zip(SECTION_KEYS, SECTION_LABELS):
            sec_rows.append([label, str(section_scores.get(key, 0)), "10"])
        sec_rows.append(["TOTAL", str(total), "40"])
        st = Table(sec_rows, colWidths=[7*cm, 2*cm, 2*cm])
        ss2 = TableStyle(_base_style())
        ss2.add("FONTNAME", (0, len(sec_rows)-1), (-1, len(sec_rows)-1), "Helvetica-Bold")
        st.setStyle(ss2)
        story.append(st)
        story.append(PageBreak())

    doc.build(story)


def _q_rows(questions, q_from, q_to, answer_key):
    q_map = {q["q_no"]: q for q in questions}
    rows = []
    for q_no in range(q_from, q_to + 1):
        q = q_map.get(q_no, {})
        marked  = q.get("marked", "—") or "—"
        correct = answer_key.get(f"q{q_no}", "?")
        tick    = "✓" if q.get("is_correct") else "✗"
        rows.append([str(q_no), marked, correct, tick])
    return rows


def generate_summary_report(all_results: List[Dict[str, Any]], output_path: str):
    """Summary PDF: all students, section scores, total marks."""
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm,  bottomMargin=1.5*cm)
    title_s, h2_s, body_s, small_s = _style()
    story = []

    story.append(Paragraph("OMR Results — All Students Summary", title_s))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Total students: {len(all_results)}", small_s))
    story.append(Spacer(1, 0.5*cm))

    headers = ["#", "Student ID", "Intelligence\n/10", "Science\n/10",
               "Social Sci\n/10", "Mathematics\n/10", "Total\n/40", "Date"]
    rows = [headers]

    # Sort by total desc
    sorted_results = sorted(all_results,
                            key=lambda r: r.get("section_scores", {}).get("total", 0),
                            reverse=True)

    for i, r in enumerate(sorted_results, 1):
        sc = r.get("section_scores", {})
        rows.append([
            str(i),
            r.get("student_id", "—"),
            str(sc.get("intelligence", 0)),
            str(sc.get("science", 0)),
            str(sc.get("social", 0)),
            str(sc.get("math", 0)),
            str(sc.get("total", 0)),
            r.get("timestamp", "")[:10],
        ])

    col_w = [0.8*cm, 4*cm, 2.2*cm, 1.8*cm, 2.2*cm, 2.5*cm, 1.8*cm, 2.2*cm]
    t = Table(rows, colWidths=col_w)
    ts = TableStyle(_base_style())

    # Highlight top 3
    top_colors = [colors.HexColor("#ffd700"), colors.HexColor("#c0c0c0"), colors.HexColor("#cd7f32")]
    for i in range(1, min(4, len(rows))):
        ts.add("BACKGROUND", (0, i), (-1, i), top_colors[i-1])

    t.setStyle(ts)
    story.append(t)
    story.append(Spacer(1, 1*cm))

    # Section averages
    if sorted_results:
        story.append(Paragraph("Section Averages", h2_s))
        avg_rows = [["Section", "Average", "Max"]]
        for key, label in zip(SECTION_KEYS, SECTION_LABELS):
            vals = [r.get("section_scores", {}).get(key, 0) for r in all_results]
            avg = sum(vals) / len(vals)
            avg_rows.append([label, f"{avg:.1f}", "10"])
        total_vals = [r.get("section_scores", {}).get("total", 0) for r in all_results]
        avg_rows.append(["TOTAL", f"{sum(total_vals)/len(total_vals):.1f}", "40"])
        avg_t = Table(avg_rows, colWidths=[7*cm, 2.5*cm, 2*cm])
        avg_t.setStyle(TableStyle(_base_style()))
        story.append(avg_t)

    doc.build(story)
