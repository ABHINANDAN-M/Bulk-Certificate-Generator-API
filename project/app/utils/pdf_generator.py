"""PDF certificate rendering with ReportLab.

Pure/synchronous and free of I/O besides reading the template, so it is trivial
to unit-test. The service layer runs it in a worker thread (asyncio.to_thread) so
CPU-bound PDF work never blocks the event loop.
"""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


@dataclass(frozen=True)
class CertificateData:
    certificate_id: str
    recipient_name: str
    course_name: str
    event_name: str
    issue_date: str  # already formatted for display
    organization_name: str
    verification_url: str


class CertificateGenerator:
    """Renders a certificate to PDF bytes. Subclass/replace for other templates (OCP)."""

    PAGE_W, PAGE_H = landscape(A4)  # 842 x 595 pt
    NAVY = colors.HexColor("#122A4C")
    GOLD = colors.HexColor("#BF9B30")

    def __init__(self, template_path: str | Path) -> None:
        self._template = Path(template_path)

    def generate(self, data: CertificateData) -> bytes:
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=landscape(A4))
        c.setTitle(f"Certificate - {data.recipient_name}")
        c.setAuthor(data.organization_name)

        self._draw_background(c)
        self._draw_text(c, data)
        self._draw_signature(c, data)
        self._draw_qr(c, data)

        c.showPage()
        c.save()
        return buf.getvalue()

    # ------------------------------------------------------------------ helpers
    def _draw_background(self, c: canvas.Canvas) -> None:
        if self._template.is_file():
            c.drawImage(
                ImageReader(str(self._template)), 0, 0,
                width=self.PAGE_W, height=self.PAGE_H, preserveAspectRatio=False,
            )
        else:  # graceful fallback so a missing template never breaks generation
            c.setStrokeColor(self.NAVY)
            c.setLineWidth(6)
            c.rect(20, 20, self.PAGE_W - 40, self.PAGE_H - 40)

    def _draw_text(self, c: canvas.Canvas, d: CertificateData) -> None:
        cx = self.PAGE_W / 2

        # Header band (navy in template) -> white organisation name
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(cx, self.PAGE_H - 62, d.organization_name.upper())

        c.setFillColor(self.NAVY)
        c.setFont("Times-Bold", 42)
        c.drawCentredString(cx, 440, "CERTIFICATE")
        c.setFont("Times-Roman", 20)
        c.drawCentredString(cx, 412, "OF COMPLETION")

        c.setFillColor(colors.HexColor("#555555"))
        c.setFont("Helvetica", 13)
        c.drawCentredString(cx, 365, "This is to certify that")

        # Recipient name: shrink-to-fit so long names never overflow the page
        size = 38
        while size > 16 and c.stringWidth(d.recipient_name, "Times-BoldItalic", size) > 640:
            size -= 2
        c.setFillColor(self.GOLD)
        c.setFont("Times-BoldItalic", size)
        c.drawCentredString(cx, 318, d.recipient_name)
        c.setStrokeColor(self.GOLD)
        c.setLineWidth(1)
        c.line(cx - 250, 306, cx + 250, 306)

        c.setFillColor(colors.HexColor("#555555"))
        c.setFont("Helvetica", 13)
        c.drawCentredString(cx, 275, "has successfully completed the course")
        c.setFillColor(self.NAVY)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(cx, 243, d.course_name)

        c.setFillColor(colors.HexColor("#555555"))
        c.setFont("Helvetica", 13)
        c.drawCentredString(cx, 212, "as part of")
        c.setFillColor(self.NAVY)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(cx, 190, d.event_name)

    def _draw_signature(self, c: canvas.Canvas, d: CertificateData) -> None:
        # Signature line (left)
        c.setStrokeColor(self.NAVY)
        c.setLineWidth(1)
        c.line(110, 135, 290, 135)
        c.setFillColor(self.NAVY)
        c.setFont("Helvetica", 10)
        c.drawCentredString(200, 121, "Authorised Signature")

        # Issue date (centre)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(self.PAGE_W / 2, 140, d.issue_date)
        c.line(self.PAGE_W / 2 - 80, 135, self.PAGE_W / 2 + 80, 135)
        c.setFont("Helvetica", 10)
        c.drawCentredString(self.PAGE_W / 2, 121, "Date of Issue")

        # Certificate ID in the footer band (white on navy)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 9)
        c.drawCentredString(self.PAGE_W / 2, 52, f"Certificate ID: {d.certificate_id}")
        c.setFont("Helvetica", 8)
        c.drawCentredString(self.PAGE_W / 2, 38, f"Verify at {d.verification_url}")

    def _draw_qr(self, c: canvas.Canvas, d: CertificateData) -> None:
        size = 80
        widget = QrCodeWidget(d.verification_url)
        x0, y0, x1, y1 = widget.getBounds()
        drawing = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
        drawing.add(widget)
        renderPDF.draw(drawing, c, self.PAGE_W - 190, 105)
        c.setFillColor(self.NAVY)
        c.setFont("Helvetica", 8)
        c.drawCentredString(self.PAGE_W - 150, 95, "Scan to verify")
