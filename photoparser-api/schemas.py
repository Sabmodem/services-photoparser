from pydantic import BaseModel
import uuid
import typing

SearchQueryStatusSheduled = 0
SearchQueryStatusProcessing = 1
SearchQueryStatusDone = 2
SearchQueryStatusError = 3

class TaskBase(BaseModel):
    id: str
    status: str

class Task(TaskBase):
    pass

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

class SearchQueryCreate(SearchQueryBase):
    pass

class SearchQuery(SearchQueryBase):
    search_results: list[SearchResult] = []
    status: SearchQueryStatus

    class Config:
        from_attributes = True