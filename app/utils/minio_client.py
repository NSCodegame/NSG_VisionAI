"""
MinIO Utility — Phase 9 (Early Implementation for Detection Snapshots)

Provides basic S3-compatible storage operations using boto3.
"""

import logging
from io import BytesIO
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

class MinIOClient:
    """
    Client for interacting with MinIO/S3 storage.
    Connection is lazy — only established on first use.
    """

    def __init__(self):
        self._client = None
        self.bucket = settings.minio_bucket_name

    def _get_client(self):
        """Lazily initialize the boto3 S3 client."""
        if self._client is None:
            endpoint = settings.minio_endpoint
            if not endpoint.startswith(('http://', 'https://')):
                endpoint = f"{'https' if settings.minio_secure else 'http'}://{endpoint}"

            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=settings.minio_access_key,
                aws_secret_access_key=settings.minio_secret_key,
                config=Config(signature_version="s3v4"),
                region_name=settings.minio_region or "us-east-1"
            )
            self._ensure_bucket_exists()
        return self._client

    @property
    def client(self):
        """Public access to the underlying boto3 client (lazy)."""
        return self._get_client()

    def _ensure_bucket_exists(self):
        """Create the bucket if it doesn't exist."""
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                logger.info("Creating MinIO bucket: %s", self.bucket)
                try:
                    self._client.create_bucket(Bucket=self.bucket)
                except ClientError as ce:
                    logger.error("Failed to create bucket: %s", ce)
            elif error_code == "503":
                logger.warning("MinIO not available yet — bucket check deferred")
            else:
                logger.warning("MinIO bucket check failed (code=%s): %s", error_code, e)

    def upload_bytes(self, data: bytes, object_name: str, content_type: str = "application/octet-stream") -> bool:
        """Upload raw bytes to MinIO."""
        try:
            self._get_client().put_object(
                Bucket=self.bucket,
                Key=object_name,
                Body=data,
                ContentType=content_type
            )
            return True
        except ClientError as e:
            logger.error("MinIO upload failed: %s", e)
            return False
        except Exception as e:
            logger.error("MinIO upload error: %s", e)
            return False

    def get_presigned_url(self, object_name: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned URL for temporary access to an object."""
        try:
            return self._get_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_name},
                ExpiresIn=expires_in
            )
        except ClientError:
            return None
        except Exception:
            return None


minio_client = MinIOClient()
