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


class SearchQueryStatusAdmin(ModelView, model=models.SearchQueryStatus):
    column_list = [models.SearchQueryStatus.id, models.SearchQueryStatus.description]
    column_labels = {
        models.SearchQueryStatus.id: "ID",
        models.SearchQueryStatus.description: "Description",
    }
    name = "Statuses"
    name_plural = "Statuses"


class SearchResultAdmin(ModelView, model=models.SearchResult):
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
        "safe_search": {"choices": SAFE_SEARCH_OPTIONS},
    }

    async def on_model_change(self, data: dict, model: models.SearchQuery, is_created: bool, request: Request) -> None:
        """Enqueue search job when a new query is created."""
        if is_created:
            try:
                q.enqueue(
                    search_job,
                    str(data.get("query_string", "")),
                    int(data.get("pages", 1)),
                    str(data.get("time_range", "")),
                    str(data.get("language", "")),
                    str(model.id),
                    job_timeout=300,
                )
                print(f"Enqueued search job: {data.get('query_string')} (id={model.id})")
            except Exception as e:
                print(f"Failed to enqueue search job: {e}")

        # Always call parent to preserve default behavior
        await super().on_model_change(data, model, is_created, request)


def init_admin(app):
    admin = Admin(app, engine=engine, base_url="/admin")
    admin.add_view(SearchQueryStatusAdmin)
    admin.add_view(SearchResultAdmin)
    admin.add_view(SearchQueryAdmin)
    return admin
