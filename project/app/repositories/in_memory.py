"""In-memory repositories: used by the test-suite (no DB needed) and for local experiments.

They implement the same interfaces as the Mongo repositories, which is the whole
point of the Repository Pattern.
"""
from datetime import datetime

from app.models.documents import CertificateDocument, JobDocument
from app.models.enums import CertificateStatus, JobStatus
from app.repositories.base import CertificateRepository, JobRepository


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self.jobs: dict[str, JobDocument] = {}

    async def create(self, job: JobDocument) -> JobDocument:
        self.jobs[job.job_id] = job
        return job

    async def get(self, job_id: str) -> JobDocument | None:
        job = self.jobs.get(job_id)
        return job.model_copy() if job else None

    async def set_status(
        self, job_id: str, status: JobStatus, completed_at: datetime | None = None
    ) -> None:
        job = self.jobs[job_id]
        job.status = status
        if completed_at:
            job.completed_at = completed_at

    async def increment_counts(self, job_id: str, *, success: bool) -> None:
        job = self.jobs[job_id]
        if success:
            job.success_count += 1
        else:
            job.failed_count += 1


class InMemoryCertificateRepository(CertificateRepository):
    def __init__(self) -> None:
        self.certs: dict[str, CertificateDocument] = {}

    async def create(self, cert: CertificateDocument) -> CertificateDocument:
        self.certs[cert.certificate_id] = cert
        return cert

    async def get(self, certificate_id: str) -> CertificateDocument | None:
        return self.certs.get(certificate_id)

    async def list_by_job(
        self,
        job_id: str,
        *,
        status: CertificateStatus | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[CertificateDocument], int]:
        items = [c for c in self.certs.values() if c.job_id == job_id]
        if status:
            items = [c for c in items if c.status == status]
        if search:
            items = [c for c in items if search.lower() in c.recipient_name.lower()]
        items.sort(key=lambda c: c.created_at)
        return items[skip : skip + limit], len(items)

    async def list_failed(self, job_id: str) -> list[CertificateDocument]:
        return [
            c for c in self.certs.values()
            if c.job_id == job_id and c.status == CertificateStatus.FAILED
        ]
