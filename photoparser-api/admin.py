from starlette.requests import Request
from sqladmin import Admin, ModelView
from wtforms import SelectField

import models
from search import main as search_job
from database import engine
import redis
from rq import Queue


r = redis.Redis(host='redis', port=6379)
q = Queue(connection=r)

DEFAULT_PAGES = 2  # Minimum/default pages for a new search query


class SearchQueryStatusAdmin(ModelView, model=models.SearchQueryStatus):
    # Read-only view — statuses are a fixed lookup table managed via DB seed/alembic.
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [models.SearchQueryStatus.id, models.SearchQueryStatus.description]
    column_labels = {
        models.SearchQueryStatus.id: "ID",
        models.SearchQueryStatus.description: "Description",
    }
    name = "Statuses"
    name_plural = "Statuses"


class SearchResultAdmin(ModelView, model=models.SearchResult):
    # Read-only — results are produced by the worker, never edited manually.
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [models.SearchResult.id, models.SearchResult.thumb_src, models.SearchResult.search_query_id]
    column_labels = {
        models.SearchResult.id: "ID",
        models.SearchResult.thumb_src: "Thumbnail",
        models.SearchResult.search_query_id: "Query",
    }
    name = "Result"
    name_plural = "Results"


TIME_RANGE_OPTIONS = [
    ("day", "Day"),
    ("week", "Week"),
    ("month", "Month"),
    ("year", "Year"),
]

LANGUAGE_OPTIONS = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("ja", "Japanese"),
    ("zh", "Chinese"),
    ("pt", "Portuguese"),
    ("ru", "Russian"),
]

SAFE_SEARCH_OPTIONS = [
    (0, "Off"),
    (1, "Moderate"),
    (2, "Strict"),
]


class SearchQueryAdmin(ModelView, model=models.SearchQuery):
    # Create and delete allowed, edit forbidden (queries should not be modified after creation).
    can_create = True
    can_edit = False
    can_delete = True

    column_list = [
        models.SearchQuery.id,
        models.SearchQuery.query_string,
        models.SearchQuery.pages,
        models.SearchQuery.status,
    ]
    column_details_list = [
        models.SearchQuery.query_string,
        models.SearchQuery.pages,
        models.SearchQuery.time_range,
        models.SearchQuery.language,
        models.SearchQuery.safe_search,
        models.SearchQuery.status,
    ]
    column_labels = {
        models.SearchQuery.id: "ID",
        models.SearchQuery.query_string: "Query",
        models.SearchQuery.pages: "Pages",
        models.SearchQuery.time_range: "Time Range",
        models.SearchQuery.language: "Language",
        models.SearchQuery.safe_search: "Safe Search",
        models.SearchQuery.status: "Status",
    }
    form_columns = [
        models.SearchQuery.query_string,
        models.SearchQuery.pages,
        models.SearchQuery.time_range,
        models.SearchQuery.language,
        models.SearchQuery.safe_search,
    ]
    form_overrides = {
        "time_range": SelectField,
        "language": SelectField,
        "safe_search": SelectField,
    }
    form_args = {
        "time_range": {"choices": TIME_RANGE_OPTIONS},
        "language": {"choices": LANGUAGE_OPTIONS},
        "safe_search": {"choices": SAFE_SEARCH_OPTIONS, "coerce": int},
    }

    async def insert_model(self, request: Request, data: dict) -> models.SearchQuery:
        """Override to enqueue search job AFTER the model is persisted (has an ID)."""
        # Normalize pages: 0 or negative defaults to DEFAULT_PAGES
        data["pages"] = max(int(data.get("pages", DEFAULT_PAGES)), DEFAULT_PAGES)

        model = await super().insert_model(request, data)

        # At this point, the model has been committed and model.id is set.
        try:
            q.enqueue(
                search_job,
                str(data.get("query_string", "")),
                int(data["pages"]),
                str(data.get("time_range", "")),
                str(data.get("language", "")),
                str(model.id),
                job_timeout=300,
            )
            print(f"Enqueued search job: {data.get('query_string')} pages={data['pages']} id={model.id}")
        except Exception as e:
            print(f"Failed to enqueue search job: {e}")
        return model


def init_admin(app):
    admin = Admin(app, engine=engine, base_url="/admin")
    admin.add_view(SearchQueryStatusAdmin)
    admin.add_view(SearchResultAdmin)
    admin.add_view(SearchQueryAdmin)
    return admin
