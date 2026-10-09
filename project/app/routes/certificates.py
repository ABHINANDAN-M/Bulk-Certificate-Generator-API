"""Certificate download, verification, health and auth endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.routes.deps import get_certificate_service
from app.schemas.auth import TokenRequest, TokenResponse
from app.schemas.jobs import VerifyResponse
from app.services import auth_service
from app.services.auth_service import require_auth
from app.services.certificate_service import CertificateService

# Protected
router = APIRouter(
    prefix="/api/v1/certificates", tags=["Certificates"], dependencies=[Depends(require_auth)]
)


@router.get(
    "/{certificate_id}/download",
    summary="Download a certificate PDF",
    responses={200: {"content": {"application/pdf": {}}}, 404: {"description": "Not found"}},
)
async def download_certificate(
    certificate_id: str, service: CertificateService = Depends(get_certificate_service)
) -> Response:
    cert, pdf = await service.get_pdf(certificate_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="certificate_{cert.certificate_id}.pdf"'},
    )


# Public routes
public = APIRouter()


@public.get("/health", tags=["Health"], summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@public.get(
    "/verify/{certificate_id}",
    response_model=VerifyResponse,
    tags=["Verification"],
    summary="Verify a certificate (target of the QR code)",
)
async def verify_certificate(
    certificate_id: str, service: CertificateService = Depends(get_certificate_service)
) -> VerifyResponse:
    return await service.verify(certificate_id)


@public.post("/api/v1/auth/token", response_model=TokenResponse, tags=["Auth"], summary="Obtain a JWT")
async def login(body: TokenRequest, request: Request) -> TokenResponse:
    settings = request.app.state.settings
    if not auth_service.authenticate(settings, body.username, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return auth_service.create_token(settings, body.username)
