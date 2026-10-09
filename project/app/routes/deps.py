"""FastAPI dependencies resolving services from app.state (set up in main.create_app)."""
from fastapi import Request

from app.services.certificate_service import CertificateService
from app.services.job_service import JobService


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


def get_certificate_service(request: Request) -> CertificateService:
    return request.app.state.certificate_service
