"""Shared constants for the chat router package."""

import os

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = frozenset({
    "text/plain", "text/markdown", "text/csv", "text/html",
    "application/json", "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png", "image/jpeg", "image/gif", "image/webp",
})
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
