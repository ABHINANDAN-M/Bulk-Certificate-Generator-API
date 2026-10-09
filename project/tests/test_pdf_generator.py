"""Certificate generation (ReportLab)."""
from app.utils.pdf_generator import CertificateData, CertificateGenerator
from tests.conftest import TEMPLATE


def _data(name="Abhinandan Mahanta") -> CertificateData:
    return CertificateData(
        certificate_id="abc-123", recipient_name=name, course_name="Python Bootcamp",
        event_name="AI Workshop", issue_date="10 October 2026",
        organization_name="Example Academy", verification_url="http://localhost:8000/verify/abc-123",
    )


def test_generates_valid_pdf_bytes():
    pdf = CertificateGenerator(TEMPLATE).generate(_data())
    assert pdf.startswith(b"%PDF") and pdf.rstrip().endswith(b"%%EOF")


def test_very_long_name_does_not_crash():
    assert CertificateGenerator(TEMPLATE).generate(_data("A" * 110)).startswith(b"%PDF")


def test_missing_template_falls_back_gracefully(tmp_path):
    pdf = CertificateGenerator(tmp_path / "missing.png").generate(_data())
    assert pdf.startswith(b"%PDF")
