"""File upload + download routes for chat attachments.

In-memory `_pending_uploads` store keys uploaded files by id; messages.py
consumes entries from it when an `attachment_ids` list is supplied with a
send-message request. In production this should be Redis or similar.
"""

import asyncio
import hashlib
import os
import uuid
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..auth.router import User as AuthenticatedUser
from ..auth.router import get_current_user
from ..core.contracts import SuccessEnvelope
from ..services.pdf_extraction_service import extract_pdf
from .constants import ALLOWED_MIME_TYPES, MAX_UPLOAD_SIZE_BYTES, UPLOAD_DIR
from .schemas import FileUploadResponse

logger = structlog.get_logger()

router = APIRouter()

# Shared between this module and messages.py
_pending_uploads: Dict[str, Dict[str, Any]] = {}


def _write_bytes(path: str, contents: bytes) -> None:
    with open(path, "wb") as f:
        f.write(contents)


@router.post("/upload-file", response_model=SuccessEnvelope[FileUploadResponse])
async def upload_file(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Upload a file for later attachment to a chat message."""
    # Validate MIME type
    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {mime}")

    # Read file content (enforcing size limit)
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB",
        )

    file_id = str(uuid.uuid4())
    safe_filename = os.path.basename(file.filename or "untitled")
    file_hash = hashlib.sha256(contents).hexdigest()
    storage_key = f"chat-uploads/{current_user.id}/{file_id}/{safe_filename}"

    # Persist to local uploads directory (swap for S3 in production)
    dest_dir = os.path.join(UPLOAD_DIR, current_user.id, file_id)
    await asyncio.to_thread(os.makedirs, dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, safe_filename)
    await asyncio.to_thread(_write_bytes, dest_path, contents)

    upload_meta: Dict[str, Any] = {
        "file_id": file_id,
        "user_id": current_user.id,
        "filename": safe_filename,
        "mime_type": mime,
        "size_bytes": len(contents),
        "storage_key": storage_key,
        "upload_hash": file_hash,
        "path": dest_path,
    }
    if mime == "application/pdf":
        pdf_meta = await asyncio.to_thread(extract_pdf, dest_path)
        upload_meta.update(pdf_meta)

    _pending_uploads[file_id] = upload_meta

    logger.info(
        "file_uploaded",
        file_id=file_id,
        filename=safe_filename,
        size_bytes=len(contents),
        user_id=current_user.id,
        pdf_extraction_status=upload_meta.get("pdf_extraction_status"),
    )

    return FileUploadResponse(
        file_id=file_id,
        filename=safe_filename,
        mime_type=mime,
        size_bytes=len(contents),
    )


@router.get("/files/{file_id}")
async def download_file(
    file_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Download an uploaded file. Only the owning user can access it."""
    from fastapi.responses import FileResponse

    meta = _pending_uploads.get(file_id)
    if not meta or meta["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = meta["path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=meta["filename"],
        media_type=meta["mime_type"],
    )
