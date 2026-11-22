"""RQ job: download images from a search query and upload as a ZIP archive."""

import asyncio
import io
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
from rq import get_current_job
from sqlalchemy import select

import crud
import database
import models
import schemas
import storage

DOWNLOAD_TIMEOUT = 600  # 10 minutes
DOWNLOAD_CONCURRENCY = 5  # concurrent downloads


async def _download_image(client: httpx.AsyncClient, img_src: str, dest_path: Path) -> bool:
    """Download a single image. Returns True on success."""
    try:
        resp = await client.get(img_src, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        dest_path.write_bytes(resp.content)
        return True
    except Exception as e:
        print(f"Failed to download {img_src}: {e}")
        return False


async def main(search_query_id: str):
    """Download all images for a search query, zip them, and upload to storage."""
    async with database.SessionLocal() as db:
        try:
            search_query = await crud.get_search_query(db, uuid.UUID(search_query_id))

            # Count and fetch results
            result = await db.execute(
                select(models.SearchResult).where(
                    models.SearchResult.search_query_id == uuid.UUID(search_query_id)
                )
            )
            results = result.scalars().all()
            total = len(results)

            # Create download task
            task = await crud.create_download_task(db, uuid.UUID(search_query_id), total)
            task_id = task.id

            # Update status to "processing"
            await crud.update_download_task_status(db, task_id, schemas.SearchQueryStatusProcessing)

            if total == 0:
                await crud.fail_download_task(db, task_id, "No search results to download")
                return

            # Download images to temp dir
            query_name = search_query.query_string.replace("/", "_").replace(" ", "_")[:50]
            date_str = datetime.now().strftime("%Y%m%d")

            with tempfile.TemporaryDirectory() as tmpdir:
                img_dir = Path(tmpdir) / f"{query_name}_{date_str}"
                img_dir.mkdir(parents=True)

                # Download images concurrently
                async with httpx.AsyncClient(verify=False, timeout=30) as client:
                    semaphore = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)

                    async def download_with_sem(result):
                        async with semaphore:
                            suffix = Path(result.img_src).suffix or ".jpg"
                            dest = img_dir / f"{result.id}{suffix}"
                            return await _download_image(client, result.img_src, dest)

                    downloaded = 0
                    tasks = [download_with_sem(r) for r in results]
                    for coro in asyncio.as_completed(tasks):
                        success = await coro
                        if success:
                            downloaded += 1
                            if downloaded % 10 == 0 or downloaded == total:
                                await crud.update_download_task_progress(
                                    db, task_id, downloaded
                                )
                                print(f"Downloaded {downloaded}/{total} images")

                # Create ZIP
                zip_filename = f"query-{query_name}_{date_str}.zip"
                zip_path = Path(tmpdir) / zip_filename
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for img_file in img_dir.glob("*"):
                        zf.write(img_file, arcname=img_file.name)

                # Upload to storage
                archive_key = f"downloads/{task_id}.zip"
                zip_data = zip_path.read_bytes()
                file_dto = storage.FileDataDTO(
                    content=io.BytesIO(zip_data),
                    mime="application/zip",
                )
                await storage.get_storage().upload_file(archive_key, file_dto)

                # Mark task as done
                await crud.complete_download_task(
                    db, task_id, archive_key, zip_filename
                )
                print(f"Download task {task_id} complete: {archive_key}")

        except Exception as e:
            print(f"Download job failed: {e}")
            import traceback
            traceback.print_exc()
            # Try to update task status
            try:
                task = await crud.get_download_task(
                    db, uuid.UUID(search_query_id)
                )
                await crud.fail_download_task(db, task.id, str(e))
            except Exception:
                # Task might not have been created yet
                pass
