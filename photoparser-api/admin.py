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


# SearchQueryStatus is no longer exposed in admin.
# It is a fixed lookup table — statuses are managed via DB seed/alembic.
# class SearchQueryStatusAdmin(ModelView, model=models.SearchQueryStatus):
#     ...


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
    # Read-only: users can view queries but not edit or delete existing ones.
    # Create is allowed so new searches can be submitted via admin.
    can_edit = False
    can_delete = False
    can_create = True

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
        # Normalize pages: 0 or negative defaults to 1
        data["pages"] = max(int(data.get("pages", 1)), 1)

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
    # Statuses table is hidden — it's a fixed lookup (Pending/In Progress/Completed/Failed)
    admin.add_view(SearchResultAdmin)
    admin.add_view(SearchQueryAdmin)
    return admin
