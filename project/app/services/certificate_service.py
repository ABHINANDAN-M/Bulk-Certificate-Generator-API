"""Download + verification of individual certificates."""
import logging

from app.models.documents import CertificateDocument
from app.models.enums import CertificateStatus
from app.repositories.base import CertificateRepository
from app.schemas.jobs import VerifyResponse
from app.utils.exceptions import NotFoundError
from app.utils.storage import StorageBackend

logger = logging.getLogger(__name__)


class CertificateService:
    def __init__(self, certificates: CertificateRepository, storage: StorageBackend) -> None:
        self._certs = certificates
        self._storage = storage

    async def get_pdf(self, certificate_id: str) -> tuple[CertificateDocument, bytes]:
        cert = await self._certs.get(certificate_id)
        if cert is None:
            raise NotFoundError(f"Certificate {certificate_id} not found")
        if cert.status != CertificateStatus.SUCCESS or not cert.file_path:
            raise NotFoundError("Certificate was not generated successfully")
        logger.info("certificate_download", extra={"certificate_id": certificate_id})
        return cert, await self._storage.read(cert.file_path)

    async def verify(self, certificate_id: str) -> VerifyResponse:
        cert = await self._certs.get(certificate_id)
        if cert is None or cert.status != CertificateStatus.SUCCESS:
            logger.info("certificate_verify_invalid", extra={"certificate_id": certificate_id})
            return VerifyResponse(valid=False)
        logger.info("certificate_verify_valid", extra={"certificate_id": certificate_id})
        return VerifyResponse(
            valid=True,
            recipient=cert.recipient_name,
            course_name=cert.course_name,
            event_name=cert.event_name,
            issue_date=cert.issue_date,
            certificate_id=cert.certificate_id,
        )
