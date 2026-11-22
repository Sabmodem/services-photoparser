"""
Test the admin interface using TestClient to reproduce datatype mismatch
when creating a SearchQuery via the sqladmin form.

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


@pytest.fixture(autouse=True)
async def seed_statuses():
    """Ensure default statuses exist in the database."""
    async with database.engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM search_query_status WHERE id = 0"))
        count = result.scalar()
        if count == 0:
            for sid, desc in [(0, "Pending"), (1, "In Progress"), (2, "Completed"), (3, "Failed")]:
                await conn.execute(
                    text("INSERT INTO search_query_status (id, description) VALUES (:id, :desc)"),
                    {"id": sid, "desc": desc},
                )
            await conn.commit()


@pytest.mark.asyncio
async def test_create_search_query_via_admin_form():
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
        async with database.engine.connect() as conn:
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

        # Assert: create should succeed (200 or redirect)
        assert response.status_code in (200, 301, 302, 303, 307, 308), \
            f"Form submission returned {response.status_code} — see output above for the error"
