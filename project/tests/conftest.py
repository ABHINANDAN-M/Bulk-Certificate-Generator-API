"""Shared fixtures. Tests use in-memory repositories + tmp storage: no MongoDB needed."""
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repositories.in_memory import InMemoryCertificateRepository, InMemoryJobRepository
from app.utils.pdf_generator import CertificateData, CertificateGenerator
from app.utils.storage import LocalStorage

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "certificate_template.png"


class FlakyGenerator(CertificateGenerator):
    """Raises for any recipient whose name contains 'Fail' -> simulates a bad certificate."""

    def generate(self, data: CertificateData) -> bytes:
        if "Fail" in data.recipient_name:
            raise RuntimeError("simulated rendering error")
        return super().generate(data)


@dataclass
class Env:
    client: TestClient
    jobs: InMemoryJobRepository
    certs: InMemoryCertificateRepository
    root: Path
    settings: Settings


@pytest.fixture
def make_env(tmp_path):
    def _make(generator=None, **settings_overrides) -> Env:
        root = tmp_path / "certificates"
        values = dict(
            auth_enabled=False,
            certificates_dir=str(root),
            template_path=str(TEMPLATE),
            rate_limit_per_minute=10_000,
            jwt_secret="test-secret",
            admin_username="admin",
            admin_password="pw",
        )
        values.update(settings_overrides)
        settings = Settings(_env_file=None, **values)
        jobs, certs = InMemoryJobRepository(), InMemoryCertificateRepository()
        app = create_app(
            settings,
            job_repo=jobs,
            certificate_repo=certs,
            storage=LocalStorage(root),
            generator=generator or CertificateGenerator(TEMPLATE),
        )
        return Env(TestClient(app), jobs, certs, root, settings)

    return _make


@pytest.fixture
def env(make_env) -> Env:
    return make_env()


@pytest.fixture
def payload() -> dict:
    return {
        "course_name": "Python Bootcamp",
        "event_name": "AI Workshop",
        "issue_date": "2026-10-10",
        "recipients": [
            {"name": "Abhinandan Mahanta", "email": "abhi@gmail.com"},
            {"name": "John Doe", "email": "john@example.com"},
            {"name": "Jane Smith", "email": "jane@example.com"},
        ],
    }
