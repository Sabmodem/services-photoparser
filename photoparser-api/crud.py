from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import models, schemas
import sqlalchemy
import database
import uuid

async def set_search_query_status(db: AsyncSession, search_query_id: uuid.UUID, search_query_status_id: int):
    search_query = await get_search_query(db, search_query_id=search_query_id)
    search_query.status_id = search_query_status_id
    db.add(search_query)
    await db.commit()
    await db.refresh(search_query)
    return search_query

async def get_search_query(db: AsyncSession, search_query_id: uuid.UUID):
    result = await db.execute(select(models.SearchQuery).where(models.SearchQuery.id == search_query_id))
    return result.scalars().one()

async def get_search_queries(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.SearchQuery).order_by(models.SearchQuery.id.desc()).offset(skip).limit(limit))
    total = await count(db, models.SearchQuery)
    return { 'result': result.scalars().all(), 'total': total }

async def create_search_query(db: AsyncSession, search_query: schemas.SearchQueryCreate):
    db_search_query = models.SearchQuery(**search_query.dict())
    db.add(db_search_query)
    await db.commit()
    await db.refresh(db_search_query)
    return db_search_query

async def get_search_result(db: AsyncSession, search_result_id: uuid.UUID):
    result = await db.execute(select(models.SearchResult).where(models.SearchResult.id == search_result_id))
    return result.scalars().one()

async def get_search_results(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.SearchResult).order_by(models.SearchResult.id.desc()).offset(skip).limit(limit))
    total = await count(db, models.SearchResult)
    return { 'result': result.scalars().all(), 'total': total }

async def count(db: AsyncSession, table: database.Base):
    result = await db.execute(select(sqlalchemy.func.count()).select_from(table))
    return result.scalars().one()

async def create_search_result(db: AsyncSession, search_result: schemas.SearchResultCreate, search_query_id: uuid.UUID):
    db_item = models.SearchResult(**search_result.dict(), search_query_id=search_query_id)
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


async def create_download_task(db: AsyncSession, search_query_id: uuid.UUID, total: int) -> models.DownloadTask:
    db_item = models.DownloadTask(search_query_id=search_query_id, total=total)
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


async def get_download_task(db: AsyncSession, download_task_id: uuid.UUID) -> models.DownloadTask:
    result = await db.execute(select(models.DownloadTask).where(models.DownloadTask.id == download_task_id))
    return result.scalars().one()


async def get_download_tasks(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.DownloadTask).order_by(models.DownloadTask.created_at.desc()).offset(skip).limit(limit))
    total = await count(db, models.DownloadTask)
    return {'result': result.scalars().all(), 'total': total}


async def update_download_task_status(db: AsyncSession, download_task_id: uuid.UUID, status_id: int) -> models.DownloadTask:
    task = await get_download_task(db, download_task_id)
    task.status_id = status_id
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_download_task_progress(db: AsyncSession, download_task_id: uuid.UUID, downloaded: int) -> models.DownloadTask:
    task = await get_download_task(db, download_task_id)
    task.downloaded = downloaded
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def complete_download_task(db: AsyncSession, download_task_id: uuid.UUID, archive_path: str, filename: str) -> models.DownloadTask:
    task = await get_download_task(db, download_task_id)
    task.status_id = schemas.SearchQueryStatusDone
    task.archive_path = archive_path
    task.filename = filename
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def fail_download_task(db: AsyncSession, download_task_id: uuid.UUID, error_msg: str) -> models.DownloadTask:
    task = await get_download_task(db, download_task_id)
    task.status_id = schemas.SearchQueryStatusError
    task.error_msg = error_msg
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task