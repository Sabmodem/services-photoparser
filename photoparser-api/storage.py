import os
from io import BytesIO

import aiobotocore.session
from botocore.exceptions import ClientError
from botocore.config import Config

_S3_BUCKET = os.environ.get("S3_BUCKET", "")
_S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
_S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
_S3_ENDPOINT = os.environ.get("S3_ENDPOINT_URL", "")
_S3_PUBLIC_ENDPOINT = os.environ.get("S3_PUBLIC_URL", _S3_ENDPOINT)
_S3_REGION = os.environ.get("S3_REGION", "us-east-1")

if bool(_S3_BUCKET and _S3_ACCESS_KEY and _S3_SECRET_KEY and _S3_ENDPOINT) == False:
    raise RuntimeError('S3 is not configured')

_S3_CONFIG = Config(
    signature_version="s3v4",
    s3={"payload_signing_enabled": False, "addressing_style": "path"},
)

def _is_not_found(error: ClientError) -> bool:
    return error.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound")

from dataclasses import dataclass
from io import BytesIO
from typing import Optional


@dataclass
class FileDataDTO:
    content: BytesIO
    mime: str


@dataclass
class StorageFileDTO:
    storage_path: str
    mime: str
    size: int = 0

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
        self._bucket_verified = False

    def _client_kwargs(self, endpoint_url: str) -> dict:
        return {
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "endpoint_url": endpoint_url,
            "region_name": self.region,
            "config": _S3_CONFIG,
        }

    def _get_client(self):
        return self.session.create_client("s3", **self._client_kwargs(self.endpoint_url))

    def _get_public_client(self):
        return self.session.create_client(
            "s3", **self._client_kwargs(self.public_endpoint_url)
        )

    async def _ensure_bucket_exists(self):
        if self._bucket_verified:
            return
        async with self._get_client() as s3_client:
            try:
                await s3_client.head_bucket(Bucket=self.bucket_name)
            except ClientError as e:
                if _is_not_found(e):
                    await s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    raise
        self._bucket_verified = True

    async def upload_file(
        self,
        storage_path: str,
        file_data: FileDataDTO,
    ) -> str:
        await self._ensure_bucket_exists()
        # Pass the file-like object straight through so aiobotocore streams it
        # asynchronously instead of us blocking the loop with a sync .read().
        body = file_data.content
        if not hasattr(body, "read"):
            body = BytesIO(body)
        else:
            raise ValueError('probably not a file')

        async with self._get_client() as s3_client:
            await s3_client.put_object(
                Bucket=self.bucket_name,
                Key=storage_path,
                Body=body,
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
                if _is_not_found(e):
                    return False
                raise


_storage: FileStorageInterface | None = None
def get_storage() -> FileStorageInterface:
    global _storage
    if _storage is None:
        _storage = S3FileStorage(
            bucket_name=_S3_BUCKET,
            access_key=_S3_ACCESS_KEY,
            secret_key=_S3_SECRET_KEY,
            endpoint_url=_S3_ENDPOINT,
            public_endpoint_url=_S3_PUBLIC_ENDPOINT,
            region=_S3_REGION,
        )
    return _storage