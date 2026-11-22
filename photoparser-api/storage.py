"""S3-compatible and local file storage abstraction."""

import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import aiobotocore.session
from botocore.exceptions import ClientError
from botocore.config import Config

from domain.interfaces import FileStorageInterface  # type: ignore
from domain.dto import FileDataDTO, StorageFileDTO  # type: ignore


# ── Local filesystem storage (fallback / dev) ─────────────────────────────

_LOCAL_STORAGE_DIR = os.environ.get("LOCAL_STORAGE_DIR", "/tmp/photoparser-downloads")


class LocalFileStorage(FileStorageInterface):
    """Local filesystem storage — used when S3 env vars are not configured."""

    def __init__(self, base_dir: str = _LOCAL_STORAGE_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def _get_path(self, storage_path: str) -> Path:
        return self.base_dir / storage_path

    async def upload_file(
        self,
        storage_path: str,
        file_data: FileDataDTO,
    ) -> str:
        path = self._get_path(storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_data.content.read())
        return storage_path

    async def download_file(self, storage_path: str) -> FileDataDTO:
        path = self._get_path(storage_path)
        content = path.read_bytes()
        mime = "application/zip"
        if storage_path.endswith(".zip"):
            mime = "application/zip"
        elif storage_path.endswith(".jpg") or storage_path.endswith(".jpeg"):
            mime = "image/jpeg"
        elif storage_path.endswith(".png"):
            mime = "image/png"
        return FileDataDTO(content=BytesIO(content), mime=mime)

    async def delete_file(self, storage_path: str) -> bool:
        path = self._get_path(storage_path)
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False

    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> str:
        # Local file — just return the path
        return f"/storage/{storage_path}"

    async def get_upload_url(self, storage_path: str, expires_in: int = 3600) -> str:
        return self.get_file_url(storage_path, expires_in)

    async def file_exists(self, storage_path: str) -> bool:
        return self._get_path(storage_path).exists()


# ── S3 storage ─────────────────────────────────────────────────────────────

_S3_BUCKET = os.environ.get("S3_BUCKET", "")
_S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
_S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
_S3_ENDPOINT = os.environ.get("S3_ENDPOINT_URL", "")
_S3_PUBLIC_ENDPOINT = os.environ.get("S3_PUBLIC_URL", _S3_ENDPOINT)
_S3_REGION = os.environ.get("S3_REGION", "us-east-1")


def _s3_configured() -> bool:
    return bool(_S3_BUCKET and _S3_ACCESS_KEY and _S3_SECRET_KEY and _S3_ENDPOINT)


class S3FileStorage(FileStorageInterface):
    """S3-compatible storage using aiobotocore."""

    def __init__(
        self,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        public_endpoint_url: str,
        region: str = "us-east-1",
    ):
        self.bucket_name = bucket_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url
        self.public_endpoint_url = public_endpoint_url
        self.region = region

        self.session = aiobotocore.session.get_session()

    @property
    def _config(self) -> Config:
        return Config(
            signature_version="s3v4",
            s3={"payload_signing_enabled": False, "addressing_style": "path"},
        )

    async def _get_client(self):
        return self.session.create_client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            config=self._config,
        )

    async def _get_public_client(self):
        return self.session.create_client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.public_endpoint_url,
            region_name=self.region,
            config=self._config,
        )

    async def _ensure_bucket_exists(self):
        async with self._get_client() as s3_client:
            try:
                await s3_client.head_bucket(Bucket=self.bucket_name)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    await s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    raise

    async def upload_file(
        self,
        storage_path: str,
        file_data: FileDataDTO,
    ) -> str:
        await self._ensure_bucket_exists()
        async with self._get_client() as s3_client:
            await s3_client.put_object(
                Bucket=self.bucket_name,
                Key=storage_path,
                Body=file_data.content.read(),
                ContentType=file_data.mime,
                ChecksumAlgorithm="sha256",
            )
        return storage_path

    async def download_file(self, storage_path: str) -> FileDataDTO:
        async with self._get_client() as s3_client:
            response = await s3_client.get_object(
                Bucket=self.bucket_name, Key=storage_path
            )
            body = await response["Body"].read()
            mime = response.get("ContentType", "application/octet-stream")
            return FileDataDTO(content=BytesIO(body), mime=mime)

    async def delete_file(self, storage_path: str) -> bool:
        async with self._get_client() as s3_client:
            try:
                await s3_client.delete_object(
                    Bucket=self.bucket_name, Key=storage_path
                )
                return True
            except ClientError:
                return False

    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> str:
        async with self._get_public_client() as s3_client:
            return await s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": storage_path,
                },
                ExpiresIn=expires_in,
            )

    async def get_upload_url(self, storage_path: str, expires_in: int = 3600) -> str:
        async with self._get_public_client() as s3_client:
            return await s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": storage_path,
                },
                ExpiresIn=expires_in,
            )

    async def file_exists(self, storage_path: str) -> bool:
        async with self._get_client() as s3_client:
            try:
                await s3_client.head_object(
                    Bucket=self.bucket_name, Key=storage_path
                )
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                raise


# ── Factory ────────────────────────────────────────────────────────────────

_storage: FileStorageInterface | None = None


def get_storage() -> FileStorageInterface:
    global _storage
    if _storage is None:
        if _s3_configured():
            _storage = S3FileStorage(
                bucket_name=_S3_BUCKET,
                access_key=_S3_ACCESS_KEY,
                secret_key=_S3_SECRET_KEY,
                endpoint_url=_S3_ENDPOINT,
                public_endpoint_url=_S3_PUBLIC_ENDPOINT,
                region=_S3_REGION,
            )
            print(f"Storage: S3 (bucket={_S3_BUCKET}, endpoint={_S3_ENDPOINT})")
        else:
            _storage = LocalFileStorage()
            print(f"Storage: Local filesystem (dir={_LOCAL_STORAGE_DIR})")
    return _storage


def get_public_url_for(key: str) -> str:
    """Build a public URL for a stored file path.

    For S3, returns presigned URL on first call and caches it.
    For local, returns a simple path.
    """
    if _s3_configured():
        # Use a short-lived presigned URL
        storage = get_storage()
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # Cannot call sync helper from async context easily; use get_file_url
            raise RuntimeError(
                "Use get_file_url() directly in async context for presigned URLs"
            )
        else:
            # Sync-ish: create a new event loop
            import asyncio as aio
            return aio.run(_get_presigned_url(key))
    else:
        return f"/storage/{key}"


async def _get_presigned_url(key: str) -> str:
    return await get_storage().get_file_url(key, expires_in=86400)  # 24h
