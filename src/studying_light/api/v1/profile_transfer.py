"""Profile backup/restore endpoints."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from studying_light.api.v1.deps import get_current_user
from studying_light.db.models.user import User
from studying_light.db.session import get_session
from studying_light.services.profile_export import export_profile_zip_to_file
from studying_light.services.profile_import import (
    MAX_ARCHIVE_SIZE_BYTES,
    ProfileImportError,
    import_profile_zip,
)

router: APIRouter = APIRouter()

ALLOWED_ZIP_CONTENT_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
}


@router.get("/profile-export.zip")
def export_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Export current user profile as portable ZIP."""
    temp_dir = Path(tempfile.mkdtemp(prefix="studying-light-profile-export-"))
    zip_path = temp_dir / "profile-export.zip"

    try:
        export_profile_zip_to_file(session, current_user, zip_path)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="profile-export.zip",
        background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
    )


@router.post("/profile-import")
def import_profile(
    file: UploadFile = File(...),
    mode: Literal["merge", "replace"] = Query(default="merge"),
    confirm_replace: bool = Query(default=False),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Import profile ZIP for current user."""
    filename = (file.filename or "").strip().lower()
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_ZIP_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "Unsupported file content type",
                "code": "PROFILE_IMPORT_INVALID",
            },
        )
    if filename and not filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "Only .zip archives are supported",
                "code": "PROFILE_IMPORT_INVALID",
            },
        )

    content_length = file.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_ARCHIVE_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail={
                        "detail": "Archive exceeds maximum allowed size",
                        "code": "PROFILE_IMPORT_TOO_LARGE",
                    },
                )
        except ValueError:
            pass

    file_bytes = file.file.read(MAX_ARCHIVE_SIZE_BYTES + 1)
    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "Uploaded file is empty",
                "code": "PROFILE_IMPORT_INVALID",
            },
        )
    if len(file_bytes) > MAX_ARCHIVE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "detail": "Archive exceeds maximum allowed size",
                "code": "PROFILE_IMPORT_TOO_LARGE",
            },
        )

    try:
        return import_profile_zip(
            session,
            current_user,
            file_bytes,
            mode=mode,
            confirm_replace=confirm_replace,
        )
    except ProfileImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.payload()) from exc
