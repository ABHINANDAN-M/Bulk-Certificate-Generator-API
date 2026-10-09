"""Persistence models: the shape of documents stored in MongoDB."""
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.enums import CertificateStatus, JobStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class JobDocument(BaseModel):
    """Collection: jobs"""

    job_id: str = Field(default_factory=new_id)
    status: JobStatus = JobStatus.PENDING
    total_recipients: int
    success_count: int = 0
    failed_count: int = 0
    # Job-level certificate parameters (kept for auditing)
    course_name: str
    event_name: str
    issue_date: str  # ISO date string
    created_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class CertificateDocument(BaseModel):
    """Collection: certificates"""

    certificate_id: str = Field(default_factory=new_id)
    job_id: str
    recipient_name: str
    email: str
    course_name: str
    event_name: str
    issue_date: str
    status: CertificateStatus
    file_path: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
