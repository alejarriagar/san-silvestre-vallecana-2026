"""Gestión local y segura de adjuntos de sesiones deportivas."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from src.database import DATABASE_PATH, create_session_attachment

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

UPLOADS_DIRECTORY = DATABASE_PATH.parent / "uploads"


class AttachmentValidationError(ValueError):
    """Error controlado al validar un adjunto."""


def save_uploaded_session_attachment(
    session_id: int,
    uploaded_file: Any,
) -> dict[str, Any]:
    """Guarda una imagen localmente y crea su registro en SQLite."""
    original_file_name = Path(uploaded_file.name).name
    suffix = Path(original_file_name).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise AttachmentValidationError(
            "Formato no permitido. Usa PNG, JPG, JPEG o WEBP."
        )

    content = uploaded_file.getvalue()
    size_bytes = len(content)

    if size_bytes == 0:
        raise AttachmentValidationError(
            "El archivo adjunto está vacío."
        )

    if size_bytes > MAX_IMAGE_SIZE_BYTES:
        raise AttachmentValidationError(
            "La imagen supera el límite de 10 MB."
        )

    UPLOADS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    stored_file_name = (
        f"session_{session_id}_{uuid4().hex}{suffix}"
    )
    stored_path = UPLOADS_DIRECTORY / stored_file_name

    try:
        stored_path.write_bytes(content)

        attachment_id = create_session_attachment(
            session_id=session_id,
            original_file_name=original_file_name,
            stored_path=str(stored_path),
            mime_type=getattr(uploaded_file, "type", None),
            size_bytes=size_bytes,
        )
    except Exception as error:
        if stored_path.exists():
            stored_path.unlink()

        raise AttachmentValidationError(
            "No se pudo guardar la imagen adjunta localmente."
        ) from error

    return {
        "id": attachment_id,
        "original_file_name": original_file_name,
        "stored_path": str(stored_path),
        "size_bytes": size_bytes,
    }
