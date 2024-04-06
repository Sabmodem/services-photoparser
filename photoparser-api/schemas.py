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