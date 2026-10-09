"""Application factory.

`create_app` accepts optional overrides so tests (and alternative deployments)
can inject in-memory repositories, a different storage backend, or a stub
certificate generator without touching any business code.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.database import Database
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.repositories.base import CertificateRepository, JobRepository
from app.repositories.mongo import MongoCertificateRepository, MongoJobRepository
from app.routes import certificates, jobs
from app.services.certificate_service import CertificateService
from app.services.job_service import JobService
from app.utils.exceptions import register_exception_handlers
from app.utils.logging import setup_logging
from app.utils.pdf_generator import CertificateGenerator
from app.utils.storage import StorageBackend, build_storage

logger = logging.getLogger(__name__)


def _wire_services(
    app: FastAPI,
    settings: Settings,
    job_repo: JobRepository,
    cert_repo: CertificateRepository,
    storage: StorageBackend,
    generator: CertificateGenerator,
) -> None:
    app.state.job_service = JobService(job_repo, cert_repo, storage, generator, settings)
    app.state.certificate_service = CertificateService(cert_repo, storage)


def create_app(
    settings: Settings | None = None,
    *,
    job_repo: JobRepository | None = None,
    certificate_repo: CertificateRepository | None = None,
    storage: StorageBackend | None = None,
    generator: CertificateGenerator | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    storage = storage or build_storage(settings)
    generator = generator or CertificateGenerator(settings.template_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db = None
        if job_repo is None or certificate_repo is None:
            # Production path: connect to MongoDB (Atlas) and build real repositories.
            db = Database(settings.mongodb_uri, settings.mongodb_db_name)
            database = await db.connect()
            jobs_repo = MongoJobRepository(database)
            certs_repo = MongoCertificateRepository(database)
            await jobs_repo.create_indexes()
            await certs_repo.create_indexes()
            _wire_services(app, settings, jobs_repo, certs_repo, storage, generator)
        logger.info("application_started", extra={"environment": settings.environment})
        yield
        if db:
            await db.disconnect()
        logger.info("application_stopped")

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Accepts bulk certificate requests, generates PDF certificates in the "
            "background, tracks progress, and serves downloads and verification."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Injected repositories (tests) are wired immediately; Mongo ones in lifespan.
    if job_repo is not None and certificate_repo is not None:
        _wire_services(app, settings, job_repo, certificate_repo, storage, generator)

    # Middleware: last added runs first -> request logging wraps everything.
    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)
    app.include_router(certificates.public)
    app.include_router(jobs.router)
    app.include_router(certificates.router)
    return app


app = create_app()
