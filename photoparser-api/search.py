import os
import httpx
import asyncio
from itertools import chain
import crud
import database
import schemas

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://searxng:8080")

async def exec(
        client,
        query,
        pageno,
        time_range,
        language,
        format
        ):
    data = {
        'q': query,
        'pageno': pageno,
        'time_range': time_range,
        'language': language,
        'format': format,
        'category_images': '1'
    }
    response = await client.post(f'{SEARXNG_URL}/search', data=data)
    json = response.json()
    return json.get('results', None)

async def main(query, pages, time, lang, id):
  async with database.SessionLocal() as db:
    await crud.set_search_query_status(db, id, schemas.SearchQueryStatusProcessing)
    async with httpx.AsyncClient(verify=False) as client:
      results_list = await asyncio.gather(*[exec(client, query, i, time, lang, 'json') for i in range(1,pages)])
      result = list(chain(*results_list))

      for r in result:
        await crud.create_search_result(db=db, search_result=schemas.SearchResultCreate(img_src=r.get('img_src', 'none'), thumb_src=r.get('thumbnail_src', 'none')), search_query_id=id)
    await crud.set_search_query_status(db, id, schemas.SearchQueryStatusDone)
