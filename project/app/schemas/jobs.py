"""Request/response schemas (API contract) for jobs."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import CertificateStatus, JobStatus

MAX_RECIPIENTS = 1000  # Hard upper bound; the runtime limit is also configurable in Settings.


class RecipientIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=3, max_length=120, examples=["Abhinandan Mahanta"])
    email: EmailStr = Field(..., examples=["abhi@gmail.com"])

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, v: str) -> str:
        return v.lower()


class BulkJobCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    course_name: str = Field(..., min_length=1, max_length=200, examples=["Python Bootcamp"])
    event_name: str = Field(..., min_length=1, max_length=200, examples=["AI Workshop"])
    issue_date: date = Field(..., examples=["2026-10-10"])
    recipients: list[RecipientIn] = Field(..., min_length=1, max_length=MAX_RECIPIENTS)

    @model_validator(mode="after")
    def _reject_duplicate_emails(self) -> "BulkJobCreate":
        """Duplicate detection (case-insensitive) within a single request."""
        seen: set[str] = set()
        duplicates: list[str] = []
        for r in self.recipients:
            if r.email in seen and r.email not in duplicates:
                duplicates.append(r.email)
            seen.add(r.email)
        if duplicates:
            raise ValueError(f"Duplicate emails in request: {', '.join(duplicates)}")
        return self


class JobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class FailedRecipient(BaseModel):
    recipient_name: str
    email: str
    error_message: str | None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    total: int
    success: int
    failed: int
    progress_percentage: float
    created_at: datetime
    completed_at: datetime | None = None
    failed_recipients: list[FailedRecipient] = []


class CertificateOut(BaseModel):
    certificate_id: str
    recipient_name: str
    email: str
    status: CertificateStatus
    error_message: str | None = None
    created_at: datetime


class VerifyResponse(BaseModel):
    valid: bool
    recipient: str | None = None
    course_name: str | None = None
    event_name: str | None = None
    issue_date: str | None = None
    certificate_id: str | None = None
