"""Business logic for bulk jobs.

Depends only on abstractions (repositories, storage, generator) -> Dependency
Inversion; each collaborator is injected so tests can swap in fakes.
"""
import asyncio
import logging
import math

from app.config import Settings
from app.models.documents import CertificateDocument, JobDocument, new_id, utcnow
from app.models.enums import CertificateStatus, JobStatus
from app.repositories.base import CertificateRepository, JobRepository
from app.schemas.jobs import BulkJobCreate, FailedRecipient, JobStatusResponse, RecipientIn
from app.utils.exceptions import NotFoundError
from app.utils.pdf_generator import CertificateData, CertificateGenerator
from app.utils.storage import StorageBackend

logger = logging.getLogger(__name__)


class JobService:
    def __init__(
        self,
        jobs: JobRepository,
        certificates: CertificateRepository,
        storage: StorageBackend,
        generator: CertificateGenerator,
        settings: Settings,
    ) -> None:
        self._jobs = jobs
        self._certs = certificates
        self._storage = storage
        self._generator = generator
        self._settings = settings

    # ------------------------------------------------------------- create / query
    async def create_job(self, payload: BulkJobCreate) -> JobDocument:
        job = JobDocument(
            total_recipients=len(payload.recipients),
            course_name=payload.course_name,
            event_name=payload.event_name,
            issue_date=payload.issue_date.isoformat(),
        )
        await self._jobs.create(job)
        logger.info(
            "job_created", extra={"job_id": job.job_id, "total": job.total_recipients}
        )
        return job

    async def get_status(self, job_id: str) -> JobStatusResponse:
        job = await self._jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"Job {job_id} not found")
        failed = await self._certs.list_failed(job_id)
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            total=job.total_recipients,
            success=job.success_count,
            failed=job.failed_count,
            progress_percentage=self.progress_percentage(job),
            created_at=job.created_at,
            completed_at=job.completed_at,
            failed_recipients=[
                FailedRecipient(
                    recipient_name=c.recipient_name, email=c.email, error_message=c.error_message
                )
                for c in failed
            ],
        )

    @staticmethod
    def progress_percentage(job: JobDocument) -> float:
        """(success + failed) / total * 100, rounded to 2dp."""
        if job.total_recipients == 0:
            return 0.0
        done = job.success_count + job.failed_count
        return round(done / job.total_recipients * 100, 2)

    async def list_certificates(
        self, job_id: str, *, status: CertificateStatus | None, search: str | None,
        page: int, page_size: int,
    ) -> tuple[list[CertificateDocument], int]:
        if await self._jobs.get(job_id) is None:
            raise NotFoundError(f"Job {job_id} not found")
        return await self._certs.list_by_job(
            job_id, status=status, search=search,
            skip=(page - 1) * page_size, limit=page_size,
        )

    # ----------------------------------------------------------------- background
    async def process_job(self, job_id: str, payload: BulkJobCreate) -> None:
        """Generate every certificate, isolating failures per recipient.

        Runs inside FastAPI BackgroundTasks after the HTTP response is sent.
        """
        logger.info("job_processing_started", extra={"job_id": job_id})
        try:
            await self._jobs.set_status(job_id, JobStatus.PROCESSING)
            success = 0
            for recipient in payload.recipients:
                ok = await self._process_recipient(job_id, payload, recipient)
                success += ok
                # progress is persisted after *every* certificate
                await self._jobs.increment_counts(job_id, success=ok)

            final = JobStatus.COMPLETED if success > 0 else JobStatus.FAILED
            await self._jobs.set_status(job_id, final, completed_at=utcnow())
            logger.info(
                "job_processing_finished",
                extra={"job_id": job_id, "status": final.value, "success": success,
                       "failed": len(payload.recipients) - success},
            )
        except Exception:  # infrastructure failure (e.g. DB down) -> mark job FAILED
            logger.exception("job_processing_crashed", extra={"job_id": job_id})
            await self._jobs.set_status(job_id, JobStatus.FAILED, completed_at=utcnow())

    async def _process_recipient(
        self, job_id: str, payload: BulkJobCreate, recipient: RecipientIn
    ) -> bool:
        """Returns True on success. NEVER raises for a per-certificate problem."""
        cert_id = new_id()
        record = CertificateDocument(
            certificate_id=cert_id,
            job_id=job_id,
            recipient_name=recipient.name,
            email=recipient.email,
            course_name=payload.course_name,
            event_name=payload.event_name,
            issue_date=payload.issue_date.isoformat(),
            status=CertificateStatus.SUCCESS,
        )
        try:
            data = CertificateData(
                certificate_id=cert_id,
                recipient_name=recipient.name,
                course_name=payload.course_name,
                event_name=payload.event_name,
                issue_date=payload.issue_date.strftime("%d %B %Y"),
                organization_name=self._settings.organization_name,
                verification_url=f"{self._settings.base_url.rstrip('/')}/verify/{cert_id}",
            )
            # CPU-bound PDF rendering -> worker thread, keeps the event loop responsive
            pdf_bytes = await asyncio.to_thread(self._generator.generate, data)
            # Storage layout: certificates/{job_id}/certificate_<uuid>.pdf
            record.file_path = await self._storage.save(
                f"{job_id}/certificate_{cert_id}.pdf", pdf_bytes
            )
            logger.info(
                "certificate_generated", extra={"job_id": job_id, "certificate_id": cert_id}
            )
        except Exception as exc:
            record.status = CertificateStatus.FAILED
            record.file_path = None
            record.error_message = f"{type(exc).__name__}: {exc}"
            logger.error(
                "certificate_failed",
                extra={"job_id": job_id, "certificate_id": cert_id,
                       "recipient": recipient.email, "error_message": record.error_message},
            )
        await self._certs.create(record)
        return record.status == CertificateStatus.SUCCESS
