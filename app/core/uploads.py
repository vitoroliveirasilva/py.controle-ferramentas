from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class UploadValidationError(ValueError):
    """Erro controlado para validação de uploads sensíveis"""


@dataclass(frozen=True)
class StoredUpload:
    original_filename: str
    storage_filename: str
    relative_path: str
    absolute_path: Path
    content_type: str
    size_bytes: int
    extension: str


_IMAGE_MAGIC = {
    "png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "jpg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "webp": lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP",
}

_DOCUMENT_MAGIC = {
    "pdf": lambda data: data.startswith(b"%PDF-"),
}

_EXTENSION_LABELS = {
    "jpeg": "JPEG",
    "jpg": "JPG",
    "pdf": "PDF",
    "png": "PNG",
    "webp": "WEBP",
}


_ALLOWED_MIME_BY_EXTENSION = {
    "jpeg": {"image/jpeg"},
    "jpg": {"image/jpeg"},
    "pdf": {"application/pdf", "application/x-pdf"},
    "png": {"image/png"},
    "webp": {"image/webp"},
}


def allowed_extensions_label(extensions: set[str]) -> str:
    labels = [
        _EXTENSION_LABELS.get(extension, extension.upper())
        for extension in sorted(extensions)
    ]
    return ", ".join(labels)


def upload_root() -> Path:
    root = Path(current_app.config["UPLOAD_BASE_DIR"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_upload_path(relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    root = upload_root()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise UploadValidationError("Caminho de upload inválido.")
    return candidate


def relative_upload_path(path: Path) -> str:
    return path.resolve().relative_to(upload_root()).as_posix()


def remove_upload_file(path: Path | None) -> None:
    if path and path.exists() and path.is_file():
        path.unlink(missing_ok=True)


def _safe_original_filename(filename: str | None, default_filename: str) -> str:
    safe_original = secure_filename(filename or "") or default_filename
    if len(safe_original) <= 120:
        return safe_original
    extension = ""
    stem = safe_original
    if "." in safe_original:
        stem, extension = safe_original.rsplit(".", 1)
        extension = "." + extension
    return f"{stem[: 120 - len(extension)]}{extension}"


def _extension_from_filename(filename: str) -> str:
    if "." not in filename:
        raise UploadValidationError("Arquivo sem extensão permitida.")
    return filename.rsplit(".", 1)[1].lower()


def _read_size_and_head(stream: BinaryIO, *, max_bytes: int) -> tuple[int, bytes]:
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)
    head = stream.read(64)
    stream.seek(0)

    if size <= 0:
        raise UploadValidationError("Arquivo vazio.")
    if size > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise UploadValidationError(f"Arquivo excede o tamanho máximo de {max_mb} MB.")
    return size, head


def _validate_magic_bytes(extension: str, head: bytes) -> None:
    validators = {**_IMAGE_MAGIC, **_DOCUMENT_MAGIC}
    validator = validators.get(extension)
    if validator and not validator(head):
        raise UploadValidationError(
            "O conteúdo do arquivo não corresponde à extensão informada."
        )


def _validate_mimetype(extension: str, mimetype: str | None) -> str:
    normalized = (
        (mimetype or "application/octet-stream").split(";", 1)[0].strip().lower()
    )
    allowed = _ALLOWED_MIME_BY_EXTENSION.get(extension)
    if (
        allowed
        and normalized not in allowed
        and normalized != "application/octet-stream"
    ):
        raise UploadValidationError("Tipo MIME incompatível com a extensão do arquivo.")
    return normalized


def store_upload(
    file: FileStorage | None,
    *,
    allowed_extensions: set[str],
    max_mb: int,
    directory_parts: tuple[str, ...],
    default_filename: str,
) -> StoredUpload:
    if not file or not file.filename:
        raise UploadValidationError("Selecione um arquivo para enviar.")

    safe_original = _safe_original_filename(file.filename, default_filename)
    extension = _extension_from_filename(safe_original)
    normalized_extensions = {item.lower().lstrip(".") for item in allowed_extensions}
    if extension not in normalized_extensions:
        allowed = allowed_extensions_label(normalized_extensions)
        raise UploadValidationError(
            f"Formato inválido. Extensões permitidas: {allowed}."
        )

    max_bytes = int(max_mb) * 1024 * 1024
    size_bytes, head = _read_size_and_head(file.stream, max_bytes=max_bytes)
    _validate_magic_bytes(extension, head)
    content_type = _validate_mimetype(extension, file.mimetype)

    destination_dir = upload_root().joinpath(*directory_parts).resolve()
    root = upload_root()
    if destination_dir != root and root not in destination_dir.parents:
        raise UploadValidationError("Diretório de upload inválido.")
    destination_dir.mkdir(parents=True, exist_ok=True)

    storage_filename = f"{uuid4().hex}_{safe_original}"
    destination = (destination_dir / storage_filename).resolve()
    if root not in destination.parents:
        raise UploadValidationError("Caminho final de upload inválido.")

    try:
        file.save(destination)
    except Exception:
        remove_upload_file(destination)
        raise

    return StoredUpload(
        original_filename=safe_original,
        storage_filename=storage_filename,
        relative_path=relative_upload_path(destination),
        absolute_path=destination,
        content_type=content_type,
        size_bytes=size_bytes,
        extension=extension,
    )
