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
