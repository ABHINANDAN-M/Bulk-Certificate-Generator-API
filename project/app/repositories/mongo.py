"""MongoDB implementations of the repositories (Motor, fully async)."""
import re
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.documents import CertificateDocument, JobDocument
from app.models.enums import CertificateStatus, JobStatus
from app.repositories.base import CertificateRepository, JobRepository

_NO_ID = {"_id": 0}  # never leak Mongo's ObjectId into the domain layer


class MongoJobRepository(JobRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["jobs"]

    async def create_indexes(self) -> None:
        await self._col.create_index("job_id", unique=True)

    async def create(self, job: JobDocument) -> JobDocument:
        await self._col.insert_one(job.model_dump(mode="python"))
        return job

    async def get(self, job_id: str) -> JobDocument | None:
        doc = await self._col.find_one({"job_id": job_id}, _NO_ID)
        return JobDocument(**doc) if doc else None

    async def set_status(
        self, job_id: str, status: JobStatus, completed_at: datetime | None = None
    ) -> None:
        update: dict = {"status": status.value}
        if completed_at:
            update["completed_at"] = completed_at
        await self._col.update_one({"job_id": job_id}, {"$set": update})

    async def increment_counts(self, job_id: str, *, success: bool) -> None:
        field = "success_count" if success else "failed_count"
        await self._col.update_one({"job_id": job_id}, {"$inc": {field: 1}})


class MongoCertificateRepository(CertificateRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["certificates"]

    async def create_indexes(self) -> None:
        await self._col.create_index("certificate_id", unique=True)
        await self._col.create_index([("job_id", 1), ("status", 1)])
        await self._col.create_index([("job_id", 1), ("recipient_name", 1)])

    async def create(self, cert: CertificateDocument) -> CertificateDocument:
        await self._col.insert_one(cert.model_dump(mode="python"))
        return cert

    async def get(self, certificate_id: str) -> CertificateDocument | None:
        doc = await self._col.find_one({"certificate_id": certificate_id}, _NO_ID)
        return CertificateDocument(**doc) if doc else None

    async def list_by_job(
        self,
        job_id: str,
        *,
        status: CertificateStatus | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[CertificateDocument], int]:
        query: dict = {"job_id": job_id}
        if status:
            query["status"] = status.value
        if search:
            # re.escape prevents regex injection from user-supplied search text
            query["recipient_name"] = {"$regex": re.escape(search), "$options": "i"}

        total = await self._col.count_documents(query)
        cursor = self._col.find(query, _NO_ID).sort("created_at", 1).skip(skip).limit(limit)
        items = [CertificateDocument(**d) async for d in cursor]
        return items, total

    async def list_failed(self, job_id: str) -> list[CertificateDocument]:
        cursor = self._col.find(
            {"job_id": job_id, "status": CertificateStatus.FAILED.value}, _NO_ID
        )
        return [CertificateDocument(**d) async for d in cursor]
