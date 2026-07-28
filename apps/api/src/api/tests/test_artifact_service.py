from __future__ import annotations

from api.artifact_service import ArtifactService


def _service_without_external_clients():
    service = ArtifactService.__new__(ArtifactService)
    service.max_artifact_size_mb = 10
    return service


def test_guess_content_type_for_known_extensions():
    service = _service_without_external_clients()

    assert service._guess_content_type("output.json") == "application/json"
    assert service._guess_content_type("run.log") == "text/plain"
    assert service._guess_content_type("data.txt") == "text/plain"
    assert service._guess_content_type("bundle.zip") == "application/zip"
    assert service._guess_content_type("backup.tar") == "application/x-tar"
    assert service._guess_content_type("archive.gz") == "application/gzip"
    assert service._guess_content_type("report.pdf") == "application/pdf"
    assert service._guess_content_type("photo.png") == "image/png"
    assert service._guess_content_type("photo.jpg") == "image/jpeg"
    assert service._guess_content_type("photo.jpeg") == "image/jpeg"


def test_guess_content_type_falls_back_for_unknown_or_missing_extensions():
    service = _service_without_external_clients()

    assert service._guess_content_type("IMAGE.PNG") == "image/png"
    assert service._guess_content_type("binary.xyz") == "application/octet-stream"
    assert service._guess_content_type("README") == "application/octet-stream"
    assert service._guess_content_type("file.") == "application/octet-stream"


def test_validate_artifact_size_returns_false_for_missing_file():
    service = _service_without_external_clients()

    assert service.validate_artifact_size("/nonexistent/path/file.bin") is False
