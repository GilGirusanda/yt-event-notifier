import logging
import os
import tempfile
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite
import boto3

from src.db.schema import init_schema

logger = logging.getLogger(__name__)

_connection: aiosqlite.Connection | None = None


def _s3():
    return boto3.client("s3")


def _s3_coords() -> tuple[str, str]:
    return os.environ["S3_BUCKET"], os.environ.get("S3_DB_KEY", "db/streams.db")


async def _download_db() -> str:
    if os.environ.get("APP_PROFILE", "dev").lower() == "dev":
        return "local_dev.db"

    bucket, key = _s3_coords()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    if bucket:
        try:
            _s3().download_file(bucket, key, path)
            logger.info("Downloaded DB from s3://%s/%s", bucket, key)
        except _s3().exceptions.NoSuchKey:
            logger.info("No existing DB in S3; starting fresh")
    return path


async def _upload_db(path: str) -> None:
    if os.environ.get("APP_PROFILE", "dev").lower() == "dev":
        return

    bucket, key = _s3_coords()
    if bucket:
        _s3().upload_file(path, bucket, key)
        logger.info("Uploaded DB to s3://%s/%s", bucket, key)


@asynccontextmanager
async def db_context() -> AsyncGenerator[aiosqlite.Connection, None]:
    global _connection
    path = await _download_db()
    _connection = await aiosqlite.connect(path)
    _connection.row_factory = aiosqlite.Row
    await init_schema(_connection)
    try:
        yield _connection
    finally:
        await _connection.close()
        _connection = None
        await _upload_db(path)


def get_connection() -> aiosqlite.Connection:
    if _connection is None:
        raise RuntimeError("No active DB connection — call within db_context()")
    return _connection
