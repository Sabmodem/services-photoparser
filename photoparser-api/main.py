from fastapi import Depends, FastAPI, HTTPException
# from sqlalchemy.orm import Session

import sqlalchemy

import crud, models, schemas
from database import SessionLocal

import uuid

from search import main as search

import redis
from rq import Queue

from time import sleep

app = FastAPI()

r = redis.Redis(host='redis', port=6379)
q = Queue(connection=r)

async def get_db():
    async with SessionLocal() as session:
        yield session

@app.post("/search_query/", response_model=schemas.SearchQuery)
async def create_user(
    search_query: schemas.SearchQueryCreate,
    pages: int,
    time: str,
    lang: str,
    db = Depends(get_db)
):
    try:
        db_search_query = await crud.create_search_query(db=db, search_query=search_query)
        q.enqueue(search, db_search_query.query_string, pages, time, lang, db_search_query.id)
        return db_search_query
    except sqlalchemy.exc.IntegrityError as e:
        raise HTTPException(status_code=400)

@app.get("/search_query/", response_model=list[schemas.SearchQuery])
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

@app.get("/search_results/", response_model=list[schemas.SearchResult])
async def read_items(skip: int = 0, limit: int = 100, db = Depends(get_db)):
    search_results = await crud.get_search_results(db, skip=skip, limit=limit)
    return search_results

@app.get("/search_results/{search_result_id}", response_model=schemas.SearchResult)
async def read_user(search_result_id: uuid.UUID, db = Depends(get_db)):
    try:
        return await crud.get_search_result(db, search_result_id=search_result_id)
    except sqlalchemy.exc.NoResultFound as e:
        raise HTTPException(status_code=404)