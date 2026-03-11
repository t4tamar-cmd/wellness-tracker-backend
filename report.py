import io
import os
import smtplib
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database import Company, SessionLocal


def generate_weekly_report_pdf() -> bytes | None:
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        companies = (
            db.query(Company)
            .filter(Company.scan_date >= cutoff)
            .order_by(Company.scan_date.desc())
            .all()
        )

        if not companies:
            return None

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
        )

        styles = getSampleStyleSheet()
        wrap_style = ParagraphStyle(
            "wrap",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
        )

        elements = []

        title = Paragraph(
            f"Weekly Wellness App Report — {datetime.utcnow().strftime('%B %d, %Y')}",
            styles["Title"],
        )
        elements.append(title)
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(
            Paragraph(
                f"{len(companies)} new wellness apps discovered in the last 7 days.",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 0.25 * inch))

        header = ["Name", "URL", "Business Model", "Uses AI", "AI Details", "Description"]
        rows = [header]

        for c in companies:
            rows.append([
                Paragraph(c.name or "", wrap_style),
                Paragraph(f'<a href="{c.url}" color="#4F46E5">{c.url}</a>' if c.url else "", wrap_style),
                c.business_model or "unknown",
                "Yes" if c.ai_usage else "No",
                Paragraph(c.ai_details or "—", wrap_style),
                Paragraph(c.description or "—", wrap_style),
            ])

        col_widths = [1.2 * inch, 1.5 * inch, 0.9 * inch, 0.5 * inch, 1.4 * inch, 1.9 * inch]

        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ]))

        elements.append(table)
        doc.build(elements)
        return buffer.getvalue()

    finally:
        db.close()


def send_weekly_email(pdf_bytes: bytes, company_count: int) -> None:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    report_email = os.getenv("REPORT_EMAIL", "")

    if not all([smtp_user, smtp_password, report_email]):
        print("[report] Missing SMTP credentials — email not sent.")
        return

    date_str = datetime.utcnow().strftime("%B %d, %Y")
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = report_email
    msg["Subject"] = f"Weekly Wellness App Report — {date_str}"

    msg.attach(MIMEText(
        f"Hi,\n\nAttached is your weekly wellness tracker report.\n"
        f"{company_count} new apps were discovered this week.\n\n"
        f"— Wellness Tracker",
        "plain",
    ))

    attachment = MIMEBase("application", "octet-stream")
    attachment.set_payload(pdf_bytes)
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=f"wellness_report_{datetime.utcnow().strftime('%Y-%m-%d')}.pdf",
    )
    msg.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, report_email, msg.as_string())

    print(f"[report] Weekly email sent to {report_email}")


def generate_and_email_report() -> None:
    print("[report] Generating weekly report...")
    try:
        pdf_bytes = generate_weekly_report_pdf()
        if pdf_bytes is None:
            print("[report] No companies found this week — skipping email.")
            return

        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=7)
            count = db.query(Company).filter(Company.scan_date >= cutoff).count()
        finally:
            db.close()

        send_weekly_email(pdf_bytes, count)
    except Exception as e:
        print(f"[report] Failed to generate/send report: {e}")
