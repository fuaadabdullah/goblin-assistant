"""
Input validation and sanitization utilities for Goblin Assistant API
Provides protection against XSS, injection attacks, and other input-based vulnerabilities
"""

import re
import html
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException

try:
    import bleach
except ImportError:  # pragma: no cover - exercised only in lean test envs
    bleach = None


def _strip_html_tags(value: str) -> str:
    """Best-effort tag removal when bleach is unavailable."""
    return re.sub(r"<[^>]+>", "", value)


def _clean_html(value: str, tags: Optional[list[str]] = None, attributes: Optional[Dict[str, Any]] = None, strip: bool = True) -> str:
    if bleach is not None:
        return bleach.clean(value, tags=tags or [], attributes=attributes or {}, strip=strip)
    return _strip_html_tags(value) if strip else value


class InputSanitizer:
    """Handles input sanitization and validation"""

    # Maximum allowed lengths
    MAX_MESSAGE_LENGTH = 10000  # 10KB max for chat messages
    MAX_TITLE_LENGTH = 200      # Max conversation title length
    MAX_USER_ID_LENGTH = 100    # Max user ID length

    # XSS protection patterns
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',                 # JavaScript URLs
        r'vbscript:',                   # VBScript URLs
        r'on\w+\s*=',                   # Event handlers
        r'<iframe[^>]*>.*?</iframe>',   # Iframe tags
        r'<object[^>]*>.*?</object>',   # Object tags
        r'<embed[^>]*>.*?</embed>',     # Embed tags
    ]

    # Allowed HTML tags for rich text (if needed)
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre'
    ]

    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        '*': ['class'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title'],
    }

    @classmethod
    def sanitize_chat_message(cls, content: str) -> Tuple[str, Dict[str, Any]]:
        """
        Sanitize chat message content for safe storage and display

        Args:
            content: Raw message content

        Returns:
            Tuple of (sanitized_content, validation_metadata)
        """
        if not content or not isinstance(content, str):
            raise HTTPException(
                status_code=400,
                detail="Message content must be a non-empty string"
            )

        # Check length
        if len(content) > cls.MAX_MESSAGE_LENGTH:
            raise HTTPException(
                status_code=413,
                detail=f"Message too long. Maximum {cls.MAX_MESSAGE_LENGTH} characters allowed."
            )

        # Remove null bytes and other control characters
        content = cls._remove_control_characters(content)

        # Check for dangerous patterns
        validation_metadata = {
            "original_length": len(content),
            "sanitized": False,
            "dangerous_patterns_found": [],
            "length_after_sanitization": 0
        }

        dangerous_found = []
        for pattern in cls.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if matches:
                dangerous_found.extend(matches)

        if dangerous_found:
            validation_metadata["dangerous_patterns_found"] = dangerous_found
            validation_metadata["sanitized"] = True

            # Use bleach for comprehensive HTML sanitization
            sanitized = _clean_html(
                content,
                tags=cls.ALLOWED_TAGS,
                attributes=cls.ALLOWED_ATTRIBUTES,
                strip=True
            )

            # Additional HTML entity encoding for safety
            sanitized = html.escape(sanitized, quote=True)
        else:
            # No dangerous content found, but still escape HTML entities
            sanitized = html.escape(content, quote=True)

        validation_metadata["length_after_sanitization"] = len(sanitized)

        return sanitized, validation_metadata

    @classmethod
    def sanitize_conversation_title(cls, title: str) -> str:
        """
        Sanitize conversation title

        Args:
            title: Raw title content

        Returns:
            Sanitized title
        """
        if not title or not isinstance(title, str):
            return "Untitled Conversation"

        # Check length
        if len(title) > cls.MAX_TITLE_LENGTH:
            title = title[:cls.MAX_TITLE_LENGTH - 3] + "..."

        # Remove control characters
        title = cls._remove_control_characters(title)

        # Use bleach to clean HTML tags
        title = _clean_html(title, tags=[], strip=True)

        # Basic HTML escaping
        title = html.escape(title, quote=True)

        return title.strip()

    @classmethod
    def validate_user_id(cls, user_id: Optional[str]) -> Optional[str]:
        """
        Validate and sanitize user ID

        Args:
            user_id: Raw user ID

        Returns:
            Validated user ID or None
        """
        if not user_id:
            return None

        if not isinstance(user_id, str):
            raise HTTPException(status_code=400, detail="User ID must be a string")

        if len(user_id) > cls.MAX_USER_ID_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"User ID too long. Maximum {cls.MAX_USER_ID_LENGTH} characters allowed."
            )

        # Remove control characters
        user_id = cls._remove_control_characters(user_id)

        # Only allow alphanumeric, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            raise HTTPException(
                status_code=400,
                detail="User ID contains invalid characters. Only alphanumeric, hyphens, and underscores allowed."
            )

        return user_id

    @classmethod
    def sanitize_metadata(cls, metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Sanitize metadata dictionary

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Sanitized metadata
        """
        if not metadata:
            return None

        if not isinstance(metadata, dict):
            raise HTTPException(status_code=400, detail="Metadata must be a dictionary")

        sanitized = {}
        for key, value in metadata.items():
            # Sanitize keys
            if not isinstance(key, str):
                continue
            safe_key = re.sub(r'[^\w\-_]', '', key)[:100]  # Limit key length

            # Sanitize values
            if isinstance(value, str):
                safe_value = html.escape(value, quote=True)[:1000]  # Limit value length
            elif isinstance(value, (int, float, bool)):
                safe_value = value
            else:
                # Convert complex types to string and sanitize
                safe_value = html.escape(str(value), quote=True)[:1000]

            sanitized[safe_key] = safe_value

        return sanitized

    @staticmethod
    def _remove_control_characters(text: str) -> str:
        """Remove control characters that could cause issues"""
        # Remove null bytes and other problematic control characters
        # Keep newlines and tabs for formatting
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    @classmethod
    def validate_file_path(cls, file_path: str) -> str:
        """
        Validate file path to prevent directory traversal

        Args:
            file_path: File path to validate

        Returns:
            Validated file path
        """
        if not file_path or not isinstance(file_path, str):
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Check for directory traversal attempts
        if '..' in file_path or file_path.startswith('/'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file path: directory traversal not allowed"
            )

        # Remove dangerous characters
        file_path = re.sub(r'[<>:"|?*]', '', file_path)

        return file_path

    @classmethod
    def sanitize_search_query(cls, query: str) -> str:
        """
        Sanitize search query input

        Args:
            query: Raw search query

        Returns:
            Sanitized search query
        """
        if not query or not isinstance(query, str):
            return ""

        # Limit length
        if len(query) > 500:
            query = query[:500]

        # Remove control characters
        query = cls._remove_control_characters(query)

        # Basic HTML escaping
        query = html.escape(query, quote=True)

        return query.strip()


# Convenience functions for common use cases
def sanitize_message(content: str) -> str:
    """Convenience function to sanitize chat messages"""
    sanitized, _ = InputSanitizer.sanitize_chat_message(content)
    return sanitized


def sanitize_title(title: str) -> str:
    """Convenience function to sanitize titles"""
    return InputSanitizer.sanitize_conversation_title(title)


def validate_and_sanitize_user_input(message: str, title: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Comprehensive input validation and sanitization

    Returns:
        Dict with sanitized inputs and validation metadata
    """
    result = {}

    # Sanitize message
    sanitized_message, message_metadata = InputSanitizer.sanitize_chat_message(message)
    result["message"] = sanitized_message
    result["message_metadata"] = message_metadata

    # Sanitize title if provided
    if title:
        result["title"] = InputSanitizer.sanitize_conversation_title(title)

    # Validate user ID if provided
    if user_id:
        result["user_id"] = InputSanitizer.validate_user_id(user_id)

    return result
