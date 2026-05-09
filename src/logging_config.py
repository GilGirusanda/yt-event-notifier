import logging
import os
import threading
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import boto3


class _S3RotatingHandler(TimedRotatingFileHandler):
    """Rotates daily and uploads each rotated file to S3 in a background thread."""

    def __init__(self, filename: str, bucket: str, s3_prefix: str = "logs/", **kwargs):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, **kwargs)
        self._bucket = bucket
        self._s3_prefix = s3_prefix

    def rotate(self, source: str, dest: str) -> None:
        super().rotate(source, dest)
        threading.Thread(target=self._upload, args=(dest,), daemon=True).start()

    def _upload(self, filepath: str) -> None:
        key = self._s3_prefix + os.path.basename(filepath)
        try:
            boto3.client("s3").upload_file(filepath, self._bucket, key)
            logging.getLogger(__name__).info("Uploaded log to s3://%s/%s", self._bucket, key)
        except Exception:
            logging.getLogger(__name__).exception("Failed to upload rotated log to S3")


def setup_logging(level: int = logging.INFO) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    root = logging.getLogger()
    if root.handlers:
        return  # already configured (e.g. Lambda container reuse)
    root.setLevel(level)

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    root.addHandler(stream)

    # File + S3 rotation only makes sense outside Lambda (container is ephemeral there).
    bucket = os.getenv("LOG_BUCKET")
    if bucket and not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        log_file = os.getenv("LOG_FILE", "logs/app.log")
        file_handler = _S3RotatingHandler(
            filename=log_file,
            bucket=bucket,
            s3_prefix="logs/",
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
