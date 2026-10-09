"""Repository interfaces (Dependency Inversion): services depend on these, not on Mongo."""
from abc import ABC, abstractmethod
from datetime import datetime

from app.models.documents import CertificateDocument, JobDocument
from app.models.enums import CertificateStatus, JobStatus


class JobRepository(ABC):
    @abstractmethod
    async def create(self, job: JobDocument) -> JobDocument: ...

    @abstractmethod
    async def get(self, job_id: str) -> JobDocument | None: ...

    @abstractmethod
    async def set_status(
        self, job_id: str, status: JobStatus, completed_at: datetime | None = None
    ) -> None: ...

    @abstractmethod
    async def increment_counts(self, job_id: str, *, success: bool) -> None:
        """Atomically bump success_count or failed_count by one."""


class CertificateRepository(ABC):
    @abstractmethod
    async def create(self, cert: CertificateDocument) -> CertificateDocument: ...

    @abstractmethod
    async def get(self, certificate_id: str) -> CertificateDocument | None: ...

    @abstractmethod
    async def list_by_job(
        self,
        job_id: str,
        *,
        status: CertificateStatus | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[CertificateDocument], int]:
        """Return (page_items, total_matching) with optional filtering/name search."""

    @abstractmethod
    async def list_failed(self, job_id: str) -> list[CertificateDocument]: ...
