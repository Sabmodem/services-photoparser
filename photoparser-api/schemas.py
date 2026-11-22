from pydantic import BaseModel
import uuid
import typing

SearchQueryStatusSheduled = 0
SearchQueryStatusProcessing = 1
SearchQueryStatusDone = 2
SearchQueryStatusError = 3

class SearchQueryStatus(BaseModel):
    id: int
    description: str

class SearchResultBase(BaseModel):
    id: typing.Optional[uuid.UUID] = None
    img_src: str
    thumb_src: str

class SearchResultCreate(SearchResultBase):
    pass

class SearchResult(SearchResultBase):
    search_query_id: typing.Optional[uuid.UUID] = None

    class Config:
        from_attributes = True

class searchResultsPaginated(BaseModel):
    results: list[SearchResult] = []
    total: int = 0

class SearchQueryBase(BaseModel):
    id: typing.Optional[uuid.UUID] = None
    query_string: str
    pages: int
    time_range: str
    language: str
    safe_search: int

class SearchQueryCreate(SearchQueryBase):
    pass

class SearchQuery(SearchQueryBase):
    search_results: list[SearchResult] = []
    status: SearchQueryStatus

    class Config:
        from_attributes = True

class SearchQueriesPaginated(BaseModel):
    results: list[SearchQuery] = []
    total: int = 0


class DownloadTaskBase(BaseModel):
    id: typing.Optional[uuid.UUID] = None
    search_query_id: uuid.UUID
    status_id: int = 0
    archive_path: typing.Optional[str] = None
    filename: typing.Optional[str] = None
    total: int = 0
    downloaded: int = 0
    error_msg: typing.Optional[str] = None


class DownloadTaskCreate(DownloadTaskBase):
    pass


class DownloadTask(DownloadTaskBase):
    created_at: typing.Optional[str] = None
    status: typing.Optional[SearchQueryStatus] = None

    class Config:
        from_attributes = True


class DownloadTasksPaginated(BaseModel):
    results: list[DownloadTask] = []
    total: int = 0
