"""Background processing: lifecycle, progress tracking, storage layout."""
import re

from app.models.enums import JobStatus
from app.schemas.jobs import BulkJobCreate
from app.services.job_service import JobService
from app.utils.pdf_generator import CertificateGenerator
from app.utils.storage import LocalStorage
from app.repositories.in_memory import InMemoryCertificateRepository, InMemoryJobRepository
from tests.conftest import TEMPLATE
from app.config import Settings


def test_pdfs_stored_under_job_folder_with_expected_name(env, payload):
    job_id = env.client.post("/api/v1/jobs", json=payload).json()["job_id"]
    files = list((env.root / job_id).glob("*.pdf"))
    assert len(files) == 3
    assert all(re.fullmatch(r"certificate_[0-9a-f-]{36}\.pdf", f.name) for f in files)


def test_job_lifecycle_timestamps_and_status(env, payload):
    job_id = env.client.post("/api/v1/jobs", json=payload).json()["job_id"]
    job = env.jobs.jobs[job_id]
    assert job.status == JobStatus.COMPLETED
    assert job.completed_at is not None and job.completed_at >= job.created_at


async def test_progress_updates_after_each_certificate(tmp_path):
    """Spy on the repo: progress must be persisted after every single certificate."""
    snapshots: list[float] = []

    class SpyJobs(InMemoryJobRepository):
        async def increment_counts(self, job_id, *, success):
            await super().increment_counts(job_id, success=success)
            snapshots.append(JobService.progress_percentage(self.jobs[job_id]))

    jobs = SpyJobs()
    settings = Settings(_env_file=None, auth_enabled=False)
    service = JobService(
        jobs, InMemoryCertificateRepository(), LocalStorage(tmp_path),
        CertificateGenerator(TEMPLATE), settings,
    )
    payload = BulkJobCreate(
        course_name="C", event_name="E", issue_date="2026-10-10",
        recipients=[{"name": f"Person {i}", "email": f"p{i}@example.com"} for i in range(4)],
    )
    job = await service.create_job(payload)
    assert job.status == JobStatus.PENDING

    await service.process_job(job.job_id, payload)

    assert snapshots == [25.0, 50.0, 75.0, 100.0]
    assert jobs.jobs[job.job_id].status == JobStatus.COMPLETED


def test_progress_percentage_formula():
    from app.models.documents import JobDocument
    job = JobDocument(total_recipients=100, success_count=60, failed_count=5,
                      course_name="c", event_name="e", issue_date="2026-01-01")
    assert JobService.progress_percentage(job) == 65
