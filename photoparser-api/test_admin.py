"""
Test the admin interface using TestClient to validate:
1. SearchQuery form submission (datatype coercion)
2. Delete cascade (SearchQuery -> SearchResult)

Run: pytest test_admin.py -v -s
"""
import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

# Override DATABASE_URL to use localhost instead of Docker hostname 'db'
os.environ["DATABASE_URL"] = "postgresql+asyncpg://photoparserx:XtCBlt3QcJ%3FL%5C9@localhost:5432/photoparser"

# Add API directory to path
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))

# Now import modules (they'll pick up the overridden DATABASE_URL)
import database
import models
from main import app


# --- Helper: create a fresh engine per test to avoid loop sharing ---
def _make_test_engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    return create_async_engine(
        "postgresql+asyncpg://photoparserx:XtCBlt3QcJ%3FL%5C9@localhost:5432/photoparser",
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# --- Session-level status seeding via direct async connection (runs once) ---
def _seed_statuses_once():
    """Run status seeding once per pytest session using asyncio.run()."""
    import asyncio

    async def _do_seed():
        engine = _make_test_engine()
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT COUNT(*) FROM search_query_status WHERE id = 0"))
                if result.scalar() == 0:
                    for sid, desc in [(0, "Pending"), (1, "In Progress"), (2, "Completed"), (3, "Failed")]:
                        await conn.execute(
                            text("INSERT INTO search_query_status (id, description) VALUES (:id, :desc)"),
                            {"id": sid, "desc": desc},
                        )
                    await conn.commit()
        finally:
            await engine.dispose()

    asyncio.run(_do_seed())


# Run seeding at import time so it's done once before any test
_seed_statuses_once()


@pytest.fixture
async def test_query():
    """Create a SearchQuery for testing, clean up after."""
    test_engine = _make_test_engine()
    async with test_engine.connect() as conn:
        result = await conn.execute(
            text("""INSERT INTO search_query (query_string, pages, status_id, time_range, language, safe_search)
                    VALUES ('test-create-form', 3, 0, 'week', 'en', 1)
                    ON CONFLICT DO NOTHING RETURNING id"""),
        )
        row = result.fetchone()
        query_id = str(row.id) if row else None
        await conn.commit()

    yield {"id": query_id}

    # Cleanup
    async with test_engine.connect() as conn:
        await conn.execute(text("DELETE FROM search_query WHERE query_string = 'test-create-form'"))
        await conn.commit()
    await test_engine.dispose()


@pytest.fixture
async def search_query_with_results():
    """Create a SearchQuery with 5 associated SearchResult rows for delete cascade testing."""
    test_engine = _make_test_engine()
    async with test_engine.connect() as conn:
        # Create query
        result = await conn.execute(
            text("""INSERT INTO search_query (query_string, pages, status_id, time_range, language, safe_search)
                    VALUES ('test-delete-cascade', 2, 0, 'week', 'en', 1)
                    ON CONFLICT DO NOTHING RETURNING id"""),
        )
        query_id = str(result.fetchone().id)

        # Insert 5 results (search_result has: id, search_query_id, img_src, thumb_src)
        for i in range(5):
            await conn.execute(
                text("""INSERT INTO search_result (img_src, thumb_src, search_query_id)
                        VALUES (:img, :thumb, :query_id) RETURNING id"""),
                {
                    "img": f"http://example.com/img_{i}",
                    "thumb": f"http://example.com/thumb_{i}",
                    "query_id": query_id,
                },
            )
        await conn.commit()

    yield {"id": query_id, "query_string": "test-delete-cascade"}

    # Cleanup
    async with test_engine.connect() as conn:
        await conn.execute(text("DELETE FROM search_result WHERE search_query_id = :qid"), {"qid": query_id})
        await conn.execute(text("DELETE FROM search_query WHERE id = :qid"), {"qid": query_id})
        await conn.commit()
    await test_engine.dispose()


# --- Tests ---

@pytest.mark.asyncio
async def test_create_search_query_via_admin_form(test_query):
    """
    Hit the sqladmin create form for SearchQuery and observe the result.

    Form fields submit as strings:
      query_string: "test-datatype-mismatch"
      pages: "3"              -> should become int(3)
      time_range: "week"      -> stays string
      language: "en"          -> stays string
      safe_search: "1"        -> coerce=int should convert to int(1)
      status_id: not in form  -> should use default=0

    If there's a datatype mismatch, we'll see a 400 error.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/admin/search-query/create",
            data={
                "query_string": "test-datatype-mismatch",
                "pages": "3",
                "time_range": "week",
                "language": "en",
                "safe_search": "1",
            },
            follow_redirects=False,
        )

        print(f"\n{'='*60}")
        print(f"Status code: {response.status_code}")
        if response.status_code in (301, 302, 303, 307, 308):
            redirect = response.headers.get("location", "N/A")
            print(f"Redirect to: {redirect}")
            resp2 = await client.get(redirect, follow_redirects=True)
            print(f"Final status: {resp2.status_code}")
            print(f"Final body (first 1500 chars):\n{resp2.text[:1500]}")
        else:
            print(f"Body (first 1500 chars):\n{response.text[:1500]}")
        print(f"{'='*60}")

        # Check what ended up in the DB
        test_engine = _make_test_engine()
        async with test_engine.connect() as conn:
            result = await conn.execute(
                models.SearchQuery.__table__.select().where(
                    models.SearchQuery.query_string == "test-datatype-mismatch"
                )
            )
            row = result.fetchone()
            if row:
                print(f"\n✓ Row inserted successfully!")
                print(f"  status_id={row.status_id} "
                      f"pages={row.pages} "
                      f"safe_search={row.safe_search} "
                      f"query_string={row.query_string}")
            else:
                print(f"\n✗ No row found — insert failed!")
        await test_engine.dispose()

        # Assert: create should succeed (200 or redirect)
        assert response.status_code in (200, 301, 302, 303, 307, 308), \
            f"Form submission returned {response.status_code} — see output above for the error"

        # Cleanup
        test_engine = _make_test_engine()
        async with test_engine.connect() as conn:
            await conn.execute(text("DELETE FROM search_query WHERE query_string = 'test-datatype-mismatch'"))
            await conn.commit()
        await test_engine.dispose()


@pytest.mark.asyncio
async def test_delete_search_query_cascades_to_results(search_query_with_results):
    """
    Verify that deleting a SearchQuery also deletes associated SearchResult rows,
    avoiding the NOT NULL constraint violation on search_query_id.

    Regression test: before fix, delete_model tried to SET search_query_id=NULL,
    which violated the NOT NULL constraint and crashed the worker.
    """
    query_id = search_query_with_results["id"]

    # Call delete_model directly (avoids ASGI event loop sharing issues)
    from admin import SearchQueryAdmin
    from starlette.requests import Request
    from uuid import UUID

    admin_view = SearchQueryAdmin()
    scope = {
        'type': 'http',
        'method': 'DELETE',
        'path': '/admin/search-query/delete',
        'query_string': b'pks=' + query_id.encode(),
        'headers': [(b'host', b'test')],
    }
    request = Request(scope)

    try:
        await admin_view.delete_model(request, query_id)
        print(f"\nDelete succeeded!")
    except Exception as e:
        print(f"\nDelete error: {type(e).__name__}: {e}")
        raise

    # Verify query is gone
    test_engine = _make_test_engine()
    async with test_engine.connect() as conn:
        q_check = await conn.execute(
            models.SearchQuery.__table__.select().where(models.SearchQuery.id == query_id)
        )
        assert q_check.fetchone() is None, "SearchQuery was not deleted!"

        # Verify all associated results are gone
        r_count = await conn.execute(
            text("SELECT COUNT(*) FROM search_result WHERE search_query_id = :qid"),
            {"qid": query_id},
        )
        assert r_count.scalar() == 0, "Associated SearchResult rows were not deleted!"

    await test_engine.dispose()

    print(f"\n✓ Delete cascade verified: query and 5 results removed")
