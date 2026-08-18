import pytest
from fastapi import HTTPException

from api.core.source_code_validation import validate_source_code


def test_validate_source_code_accepts_safe_python_source() -> None:
    source = "print('ok')"

    validated_source, report = validate_source_code(source, "python")

    assert validated_source == source
    assert report["severity"] == "ok"
    assert report["blocked_patterns"] == []


def test_validate_source_code_blocks_dangerous_python_source() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_source_code("import os\nprint('x')", "python")

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["message"] == "Source code contains blocked patterns"
    assert "os module import — potential filesystem escape" in detail["blocked"]
