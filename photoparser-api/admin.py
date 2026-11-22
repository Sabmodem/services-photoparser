from typing import Any
from uuid import UUID
from markupsafe import Markup
from starlette.requests import Request
from sqladmin import Admin, ModelView
from wtforms import SelectField

import models, schemas
from search import main as search_job
from download import main as download_job
from database import engine
import redis
from rq import Queue


r = redis.Redis(host='redis', port=6379)
q = Queue(connection=r)

DEFAULT_PAGES = 2  # Minimum/default pages for a new search query
DOWNLOAD_TIMEOUT = 600  # 10 minutes for download job


class SearchQueryStatusAdmin(ModelView, model=models.SearchQueryStatus):
    # Read-only view — statuses are a fixed lookup table managed via DB seed/alembic.
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [models.SearchQueryStatus.id, models.SearchQueryStatus.description]
    column_details_exclude_list = [models.SearchQueryStatus.search_query]
    column_labels = {
        models.SearchQueryStatus.id: "ID",
        models.SearchQueryStatus.description: "Description",
    }
    column_formatters_detail = {}
    name = "Statuses"
    name_plural = "Statuses"


class SearchResultAdmin(ModelView, model=models.SearchResult):
    # Read-only — results are produced by the worker, never edited manually.
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [
        models.SearchResult.id,
        models.SearchResult.thumb_src,
        models.SearchResult.img_src,
        models.SearchResult.search_query_id,
    ]
    column_labels = {
        models.SearchResult.id: "ID",
        models.SearchResult.thumb_src: "Thumbnail",
        models.SearchResult.img_src: "Image URL",
        models.SearchResult.search_query_id: "Query",
        models.SearchResult.search_query: "Search Query",
    }
    column_formatters = {
        models.SearchResult.thumb_src: lambda m, a: (
            Markup(f'<img src="{m.thumb_src or m.img_src}" style="max-width:200px;max-height:150px;object-fit:contain;"/>')
        ),
        models.SearchResult.img_src: lambda m, a: (
            m.img_src or m.thumb_src
        ),
        models.SearchResult.search_query_id: lambda m, a: (
            Markup(f'<a href="/admin/search-query/details/{m.search_query_id}">{m.search_query_id}</a>')
        ),
    }
    column_formatters_detail = {
        models.SearchResult.search_query: lambda m, a: (
            Markup(f'<a href="/admin/search-query/details/{m.search_query_id}">{m.search_query.query_string}</a>')
            if m.search_query and m.search_query.query_string
            else Markup(f'<a href="/admin/search-query/details/{m.search_query_id}">{m.search_query_id}</a>')
        ),
    }
    column_details_list = [
        models.SearchResult.id,
        models.SearchResult.search_query,
    ]
    page_size = 20
    page_size_options = [20, 50, 100]
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
    column_formatters = {
        models.SearchQuery.status: lambda m, a: (
            Markup(f'<a href="/admin/search-query-status/details/{m.status.id}">{m.status.description}</a>')
            if m.status and m.status.id
            else Markup(f'<a href="/admin/search-query-status/details/{m.status_id}">{m.status_id}</a>')
        ),
    }
    column_formatters_detail = {
        models.SearchQuery.status: lambda m, a: (
            Markup(f'<a href="/admin/search-query-status/details/{m.status.id}">{m.status.description}</a>')
            if m.status and m.status.description
            else Markup(f'<a href="/admin/search-query-status/details/{m.status_id}">{m.status_id}</a>')
        ),
        models.SearchQuery.id: lambda m, a: (
            Markup(
                f'<a href="/admin/download-task/new/?search_query_id={m.id}">Create Download</a>'
            )
        ),
    }
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
    name_plural = "Search Queries"
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

    async def delete_model(self, request: Request, pk: Any) -> None:
        """Delete associated SearchResult rows first to avoid NOT NULL constraint.

        We do the full delete ourselves (cascade + query delete) to avoid
        event loop sharing with other async fixtures/tests.
        """
        from sqlalchemy import delete
        from sqlalchemy.ext.asyncio import create_async_engine

        pk_uuid = UUID(str(pk))
        # Use a fresh engine to avoid event loop sharing
        cascade_engine = create_async_engine(
            engine.url,
            pool_pre_ping=True,
            pool_size=2,
        )
        try:
            async with cascade_engine.begin() as conn:
                # 1. Delete associated SearchResult rows
                await conn.execute(
                    delete(models.SearchResult).where(
                        models.SearchResult.search_query_id == pk_uuid
                    )
                )
                # 2. Delete the SearchQuery
                await conn.execute(
                    delete(models.SearchQuery).where(
                        models.SearchQuery.id == pk_uuid
                    )
                )
        finally:
            await cascade_engine.dispose()

        # Skip super().delete_model() since we already deleted everything
        await self._emit_audit(request, "delete", pk, None)

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


class DownloadTaskAdmin(ModelView, model=models.DownloadTask):
    """Download task view — read-only list, create (enqueue) and delete allowed."""
    can_create = True
    can_edit = False
    can_delete = True

    column_list = [
        models.DownloadTask.id,
        models.DownloadTask.search_query_id,
        models.DownloadTask.status,
        models.DownloadTask.total,
        models.DownloadTask.downloaded,
        models.DownloadTask.filename,
        models.DownloadTask.created_at,
    ]
    column_formatters = {
        models.DownloadTask.status: lambda m, a: (
            Markup(f'<a href="/admin/search-query-status/details/{m.status.id}">{m.status.description}</a>')
            if m.status and m.status.id
            else Markup(f'<a href="/admin/search-query-status/details/{m.status_id}">{m.status_id}</a>')
        ),
        models.DownloadTask.search_query_id: lambda m, a: (
            Markup(f'<a href="/admin/search-query/details/{m.search_query_id}">{m.search_query_id}</a>')
        ),
        models.DownloadTask.id: lambda m, a: (
            Markup(
                f'<a href="/admin/download-task/details/{m.id}">View</a>'
            )
        ),
    }
    column_formatters_detail = {
        models.DownloadTask.status: lambda m, a: (
            Markup(f'<a href="/admin/search-query-status/details/{m.status.id}">{m.status.description}</a>')
            if m.status and m.status.description
            else Markup(f'<a href="/admin/search-query-status/details/{m.status_id}">{m.status_id}</a>')
        ),
        models.DownloadTask.search_query_id: lambda m, a: (
            Markup(f'<a href="/admin/search-query/details/{m.search_query_id}">{m.search_query.query_string if m.search_query else "?"}</a>')
        ),
        models.DownloadTask.id: lambda m, a: (
            Markup(
                f'<a href="/admin/download-task/details/{m.id}">View</a>'
                + (f' <a href="/api/download_task/{m.id}/url" target="_blank">Download</a>' if m.status_id == schemas.SearchQueryStatusDone and m.archive_path else '')
            )
        ),
    }
    column_details_list = [
        models.DownloadTask.search_query,
        models.DownloadTask.status,
        models.DownloadTask.total,
        models.DownloadTask.downloaded,
        models.DownloadTask.archive_path,
        models.DownloadTask.filename,
        models.DownloadTask.error_msg,
        models.DownloadTask.created_at,
    ]
    column_labels = {
        models.DownloadTask.id: "ID",
        models.DownloadTask.search_query_id: "Query",
        models.DownloadTask.search_query: "Search Query",
        models.DownloadTask.status: "Status",
        models.DownloadTask.total: "Total",
        models.DownloadTask.downloaded: "Downloaded",
        models.DownloadTask.archive_path: "Archive Path",
        models.DownloadTask.filename: "Filename",
        models.DownloadTask.error_msg: "Error",
        models.DownloadTask.created_at: "Created",
    }
    column_searchable_list = [
        models.DownloadTask.id,
        models.DownloadTask.filename,
    ]
    column_orderable_list = [
        models.DownloadTask.created_at,
    ]
    page_size = 20
    page_size_options = [20, 50, 100]
    name = "Download Task"
    name_plural = "Download Tasks"
    form_columns = [models.DownloadTask.search_query_id]

    async def insert_model(self, request: Request, data: dict) -> models.DownloadTask:
        """Create download task and enqueue the RQ job."""
        model = await super().insert_model(request, data)
        try:
            q.enqueue(
                download_job,
                str(data.get("search_query_id", "")),
                job_timeout=DOWNLOAD_TIMEOUT,
            )
            print(f"Enqueued download job: query_id={model.search_query_id}")
        except Exception as e:
            print(f"Failed to enqueue download job: {e}")
        return model


def init_admin(app):
    admin = Admin(app, engine=engine, base_url="/admin")
    admin.add_view(SearchQueryStatusAdmin)
    admin.add_view(SearchResultAdmin)
    admin.add_view(SearchQueryAdmin)
    admin.add_view(DownloadTaskAdmin)
    return admin
