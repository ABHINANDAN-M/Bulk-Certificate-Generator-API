"""Bulk job endpoints."""
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from app.models.enums import CertificateStatus
from app.routes.deps import get_job_service
from app.schemas.jobs import (
    BulkJobCreate,
    CertificateOut,
    JobCreatedResponse,
    JobStatusResponse,
)
from app.services.auth_service import require_auth
from app.services.job_service import JobService

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"], dependencies=[Depends(require_auth)])


@router.post(
    "",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a bulk certificate generation job",
)
async def create_job(
    payload: BulkJobCreate,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(get_job_service),
) -> JobCreatedResponse:
    """Validates and stores the job, returns immediately, and generates PDFs in the background."""
    job = await service.create_job(payload)
    background_tasks.add_task(service.process_job, job.job_id, payload)
    return JobCreatedResponse(
        job_id=job.job_id, status=job.status, message="Certificate generation started"
    )


@router.get("/{job_id}", response_model=JobStatusResponse, summary="Get job status & progress")
async def get_job_status(
    job_id: str, service: JobService = Depends(get_job_service)
) -> JobStatusResponse:
    return await service.get_status(job_id)


@router.get(
    "/{job_id}/certificates",
    response_model=list[CertificateOut],
    summary="List certificates of a job (paginated, filterable, searchable)",
)
async def list_certificates(
    job_id: str,
    response: Response,
    status_filter: CertificateStatus | None = Query(None, alias="status"),
    search: str | None = Query(None, min_length=1, max_length=100, description="Name contains (case-insensitive)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: JobService = Depends(get_job_service),
) -> list[CertificateOut]:
    items, total = await service.list_certificates(
        job_id, status=status_filter, search=search, page=page, page_size=page_size
    )
    # Body stays a plain list (per the API contract); pagination metadata goes in headers.
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    return [CertificateOut(**c.model_dump()) for c in items]
