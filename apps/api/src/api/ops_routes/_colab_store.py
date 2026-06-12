"""Colab worker persistence: .env file and DB storage."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from sqlalchemy import select

logger = structlog.get_logger(__name__)

_ENV_FILE_PATH = Path(__file__).resolve().parents[5] / ".env"
_PROVIDER_NAME = "gcp_vm"


def write_env_file(key: str, value: str) -> bool:
    """Persist a key=value pair to the .env file."""
    if not _ENV_FILE_PATH.exists():
        logger.warning("env_file_not_found", path=str(_ENV_FILE_PATH))
        return False
    try:
        lines = _ENV_FILE_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
        new_line = f"{key}={value}\n"
        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                new_lines.append(new_line)
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(new_line)
        _ENV_FILE_PATH.write_text("".join(new_lines), encoding="utf-8")
        return True
    except OSError as exc:
        logger.warning("env_file_write_failed", path=str(_ENV_FILE_PATH), error=str(exc))
        return False


async def save_endpoint_to_db(endpoint: str) -> bool:
    """Persist the colab worker endpoint to the database."""
    try:
        from ..storage.database import get_db_context
        from ..storage.models import ProviderSettingsModel

        async with get_db_context() as session:
            result = await session.execute(
                select(ProviderSettingsModel).where(
                    ProviderSettingsModel.provider_name == _PROVIDER_NAME
                )
            )
            row = result.scalar_one_or_none()
            now = datetime.utcnow()
            if row:
                row.endpoint = endpoint
                row.updated_at = now
            else:
                session.add(
                    ProviderSettingsModel(
                        provider_name=_PROVIDER_NAME,
                        endpoint=endpoint,
                        updated_at=now,
                    )
                )
        return True
    except Exception as exc:
        logger.warning("colab_endpoint_db_write_failed", error=str(exc))
        return False


async def load_endpoint_from_db() -> Optional[str]:
    """Load a previously registered colab worker endpoint from the database."""
    try:
        from ..storage.database import get_db_context
        from ..storage.models import ProviderSettingsModel

        async with get_db_context() as session:
            result = await session.execute(
                select(ProviderSettingsModel).where(
                    ProviderSettingsModel.provider_name == _PROVIDER_NAME
                )
            )
            row = result.scalar_one_or_none()
            return row.endpoint if row else None
    except Exception as exc:
        logger.warning("colab_endpoint_db_read_failed", error=str(exc))
        return None
