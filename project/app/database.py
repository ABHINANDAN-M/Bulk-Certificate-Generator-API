"""MongoDB (Atlas) connection management using Motor."""
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class Database:
    """Thin wrapper around the Motor client so lifecycle is explicit and testable."""

    def __init__(self, uri: str, db_name: str) -> None:
        self._uri = uri
        self._db_name = db_name
        self._client: AsyncIOMotorClient | None = None

    async def connect(self) -> AsyncIOMotorDatabase:
        # serverSelectionTimeoutMS keeps startup failures fast and obvious.
        self._client = AsyncIOMotorClient(self._uri, serverSelectionTimeoutMS=5000)
        await self._client.admin.command("ping")  # fail fast if unreachable
        logger.info("Connected to MongoDB", extra={"db": self._db_name})
        return self._client[self._db_name]

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            logger.info("MongoDB connection closed")
