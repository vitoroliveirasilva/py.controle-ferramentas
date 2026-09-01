from __future__ import annotations

from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from app.audit.services import record_audit_log
from app.core.uploads import UploadValidationError, safe_upload_path, store_upload
from app.extensions import db
from app.reports.exporters import rows_to_csv, rows_to_xlsx, sanitize_export_value


def _file_storage(filename: str, content: bytes, mimetype: str) -> FileStorage:
    return FileStorage(
        stream=BytesIO(content), filename=filename, content_type=mimetype
    )


def test_export_values_are_sanitized_against_formula_injection():
    assert sanitize_export_value("=HYPERLINK('http://x')") == "'=HYPERLINK('http://x')"
    assert sanitize_export_value("+SUM(1,1)") == "'+SUM(1,1)"
    assert sanitize_export_value("-10") == "'-10"
    assert sanitize_export_value("@cmd") == "'@cmd"
    assert sanitize_export_value("texto seguro") == "texto seguro"


def test_csv_export_sanitizes_formula_values():
    payload = rows_to_csv([{"codigo": "=1+1", "nome": "Ferramenta"}])

    assert "'=1+1" in payload


def test_xlsx_export_sanitizes_formula_values():
    payload = rows_to_xlsx([{"codigo": "=1+1", "nome": "Ferramenta"}])

    assert payload.startswith(b"PK")


def test_upload_rejects_extension_magic_mismatch(app):
    with app.app_context():
        file = _file_storage("foto.png", b"not-a-real-png", "image/png")

        with pytest.raises(UploadValidationError):
            store_upload(
                file,
                allowed_extensions={"png"},
                max_mb=1,
                directory_parts=("tests",),
                default_filename="foto.png",
            )


def test_upload_stores_file_outside_static_under_configured_root(app, tmp_path):
    app.config["UPLOAD_BASE_DIR"] = str(tmp_path / "uploads")
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    with app.app_context():
        file = _file_storage("foto.png", png, "image/png")
        stored = store_upload(
            file,
            allowed_extensions={"png"},
            max_mb=1,
            directory_parts=("tests", "images"),
            default_filename="foto.png",
        )

        assert stored.absolute_path.exists()
        assert "static" not in stored.relative_path.split("/")
        assert safe_upload_path(stored.relative_path) == stored.absolute_path


def test_audit_log_redacts_sensitive_payload(app):
    with app.app_context():
        record = record_audit_log(
            action="security.test",
            entity="test",
            after={
                "x-api-key": "secret-key",
                "headers": {"Authorization": "Bearer token"},
                "filename": "safe.pdf",
            },
        )
        db.session.flush()

        assert "secret-key" not in record.depois
        assert "Bearer token" not in record.depois
        assert "[REDACTED]" in record.depois
        assert "safe.pdf" in record.depois
