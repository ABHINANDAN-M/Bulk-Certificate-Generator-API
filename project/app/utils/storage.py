"""Storage abstraction.

`StorageBackend` is the seam for the future AWS S3 migration: the services only
depend on this interface, so moving from local disk to S3 is a configuration
change (STORAGE_BACKEND=s3), not a code change in business logic.
"""
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import Settings
from app.utils.exceptions import NotFoundError, StorageError


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes) -> str:
        """Persist bytes under `key` and return the stored location (file_path)."""

    @abstractmethod
    async def read(self, location: str) -> bytes:
        """Read bytes back from a location previously returned by `save`."""

    @abstractmethod
    async def exists(self, location: str) -> bool: ...


class LocalStorage(StorageBackend):
    """Stores files under `<root>/<key>`, e.g. certificates/{job_id}/certificate_<uuid>.pdf."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if self._root not in path.parents:  # blocks ../ traversal
            raise StorageError("Invalid storage key")
        return path

    def _key_from_location(self, location: str) -> str:
        return location.removeprefix(f"/{self._root.name}/")

    async def save(self, key: str, data: bytes) -> str:
        path = self._safe_path(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        try:
            await asyncio.to_thread(_write)
        except OSError as exc:
            raise StorageError(f"Could not write file: {exc}") from exc
        return f"/{self._root.name}/{key}"

    async def read(self, location: str) -> bytes:
        path = self._safe_path(self._key_from_location(location))
        if not path.is_file():
            raise NotFoundError("Certificate file not found in storage")
        return await asyncio.to_thread(path.read_bytes)

    async def exists(self, location: str) -> bool:
        return self._safe_path(self._key_from_location(location)).is_file()


class S3Storage(StorageBackend):
    """AWS S3 backend (future migration path). Requires `boto3`.

    Implemented with blocking boto3 calls wrapped in threads so the event loop
    is never blocked. Stored location format: s3://<bucket>/<key>.
    """

    def __init__(self, bucket: str, region: str | None = None) -> None:
        try:
            import boto3  # lazy import: optional dependency
        except ImportError as exc:  # pragma: no cover
            raise StorageError("boto3 is required for the S3 storage backend") from exc
        self._bucket = bucket
        self._s3 = boto3.client("s3", region_name=region)

    def _key(self, location: str) -> str:
        return location.removeprefix(f"s3://{self._bucket}/")

    async def save(self, key: str, data: bytes) -> str:
        await asyncio.to_thread(
            self._s3.put_object,
            Bucket=self._bucket, Key=key, Body=data, ContentType="application/pdf",
        )
        return f"s3://{self._bucket}/{key}"

    async def read(self, location: str) -> bytes:
        obj = await asyncio.to_thread(
            self._s3.get_object, Bucket=self._bucket, Key=self._key(location)
        )
        return await asyncio.to_thread(obj["Body"].read)

    async def exists(self, location: str) -> bool:
        try:
            await asyncio.to_thread(
                self._s3.head_object, Bucket=self._bucket, Key=self._key(location)
            )
            return True
        except Exception:
            return False


def build_storage(settings: Settings) -> StorageBackend:
    """Factory selecting the backend from configuration."""
    if settings.storage_backend == "s3":
        if not settings.s3_bucket:
            raise StorageError("S3_BUCKET must be set when STORAGE_BACKEND=s3")
        return S3Storage(settings.s3_bucket, settings.s3_region)
    return LocalStorage(settings.certificates_dir)
