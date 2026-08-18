"""Shared constants for the chat router package."""

import os

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = frozenset(
    {
        "text/plain",
        "text/markdown",
        "text/csv",
        "text/html",
        "application/json",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
    }
)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")

CHAT_ARCHIVE_THRESHOLD = int(os.getenv("CHAT_ARCHIVE_THRESHOLD", "50"))
CHAT_ARCHIVE_RETAIN_LAST = int(os.getenv("CHAT_ARCHIVE_RETAIN_LAST", "10"))
CHAT_ARCHIVE_SUMMARY_MODEL = os.getenv("CHAT_ARCHIVE_SUMMARY_MODEL", "gpt-4o-mini")
CHAT_ARCHIVE_MAX_SOURCE_CHARS = int(os.getenv("CHAT_ARCHIVE_MAX_SOURCE_CHARS", "20000"))
