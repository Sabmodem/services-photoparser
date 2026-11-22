from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import sqlalchemy

import crud, models, schemas, storage
from database import SessionLocal

import uuid

from search import main as search
from download import main as download_job

import redis
from rq import Queue
from admin import init_admin
from starlette.responses import JSONResponse, RedirectResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_admin(app)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

r = redis.Redis(host='redis', port=6379)
q = Queue(connection=r)

async def get_db():
    async with SessionLocal() as session:
        yield session

@app.post("/search_query/", response_model=schemas.SearchQuery)
async def create_user(
    search_query: schemas.SearchQueryCreate,
    db = Depends(get_db)
):
    try:
        db_search_query = await crud.create_search_query(db=db, search_query=search_query)
        q.enqueue(search, db_search_query.query_string, db_search_query.pages, db_search_query.time_range, db_search_query.language, db_search_query.id)
        return db_search_query
    except sqlalchemy.exc.IntegrityError as e:
        raise HTTPException(status_code=400)

@app.get("/search_query/")
async def read_users(skip: int = 0, limit: int = 100, db = Depends(get_db)):
    search_queries = await crud.get_search_queries(db, skip=skip, limit=limit)
    return search_queries

@app.get("/search_query/{search_query_id}", response_model=schemas.SearchQuery)
async def read_user(search_query_id: uuid.UUID, db = Depends(get_db)):
    try:
        return await crud.get_search_query(db, search_query_id=search_query_id)
    except sqlalchemy.exc.NoResultFound as e:
        raise HTTPException(status_code=404)

@app.post("/search_query/{search_query_id}/search_results/", response_model=schemas.SearchResult)
async def create_item_for_user(
    search_query_id: uuid.UUID, search_result: schemas.SearchResultCreate, db = Depends(get_db)
):
    try:
        return await crud.create_search_result(db=db, search_result=search_result, search_query_id=search_query_id)
    except sqlalchemy.exc.IntegrityError as e:
        raise HTTPException(status_code=400)

@app.post("/search_query/{search_query_id}/status", response_model=schemas.SearchQuery)
async def set_search_query_status(search_query_id: uuid.UUID, search_query_status_id: int, db = Depends(get_db)):
    return await crud.set_search_query_status(db,search_query_id=search_query_id, search_query_status_id=search_query_status_id)

@app.get("/search_results/")
async def read_items(skip: int = 0, limit: int = 100, db = Depends(get_db)):
    search_results = await crud.get_search_results(db, skip=skip, limit=limit)
    return search_results

@app.get("/search_results/{search_result_id}", response_model=schemas.SearchResult)
async def read_user(search_result_id: uuid.UUID, db = Depends(get_db)):
    try:
        return await crud.get_search_result(db, search_result_id=search_result_id)
    except sqlalchemy.exc.NoResultFound as e:
        raise HTTPException(status_code=404)


# ── Download tasks ─────────────────────────────────────────────────────────

@app.post("/download_task/", response_model=schemas.DownloadTask)
async def create_download_task(
    search_query_id: uuid.UUID,
    db = Depends(get_db)
):
    """Create a download task and enqueue the RQ job."""
    try:
        task = await crud.create_download_task(db, search_query_id, 0)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid search query")

    try:
        q.enqueue(
            download_job,
            str(search_query_id),
            job_timeout=600,
        )
        print(f"Enqueued download job: query_id={search_query_id}")
    except Exception as e:
        print(f"Failed to enqueue download job: {e}")

    return task


@app.get("/download_task/", response_model=schemas.DownloadTasksPaginated)
async def read_download_tasks(skip: int = 0, limit: int = 100, db = Depends(get_db)):
    tasks = await crud.get_download_tasks(db, skip=skip, limit=limit)
    return schemas.DownloadTasksPaginated(results=tasks["result"], total=tasks["total"])


@app.get("/download_task/{download_task_id}", response_model=schemas.DownloadTask)
async def read_download_task(download_task_id: uuid.UUID, db = Depends(get_db)):
    try:
        return await crud.get_download_task(db, download_task_id)
    except sqlalchemy.exc.NoResultFound:
        raise HTTPException(status_code=404)


@app.get("/download_task/{download_task_id}/url")
async def get_download_url(download_task_id: uuid.UUID, db = Depends(get_db)):
    """Get a download URL for the archive."""
    try:
        task = await crud.get_download_task(db, download_task_id)
    except sqlalchemy.exc.NoResultFound:
        raise HTTPException(status_code=404)

    if task.status_id != schemas.SearchQueryStatusDone:
        raise HTTPException(status_code=400, detail=f"Download not ready (status: {task.status_id})")

    if not task.archive_path:
        raise HTTPException(status_code=500, detail="No archive path stored")

    url = await storage.get_storage().get_file_url(task.archive_path, expires_in=86400)
    return JSONResponse({"url": url, "filename": task.filename})