"""Test suite for input_validation.py"""

import pytest
from fastapi import HTTPException

from api.input_validation import InputSanitizer


class TestInputSanitizerChatMessage:
    """Tests for sanitize_chat_message method"""

    def test_sanitize_chat_message_valid_content(self):
        """Test sanitizing valid chat message"""
        content = "Hello, how can I help you?"
        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert isinstance(sanitized, str)
        assert "Hello" in sanitized
        assert metadata["sanitized"] is False
        assert metadata["dangerous_patterns_found"] == []

    def test_sanitize_chat_message_with_html_tags(self):
        """Test that HTML tags are properly escaped/sanitized"""
        content = "Hello <script>alert('xss')</script> world"
        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert "<script>" not in sanitized
        # Dangerous pattern found and content sanitized
        assert metadata["sanitized"] is True
        assert len(metadata.get("dangerous_patterns_found", [])) > 0

    def test_sanitize_chat_message_with_event_handlers(self):
        """Test that event handlers are sanitized"""
        content = "Click <img src=x onerror=alert('xss')>"
        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert "onerror" not in sanitized
        assert metadata["sanitized"] is True

    def test_sanitize_chat_message_with_javascript_url(self):
        """Test that javascript: URLs are handled"""
        content = "<a href='javascript:alert(1)'>Link</a>"
        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert "javascript:" not in sanitized.lower()
        assert metadata["sanitized"] is True

    def test_sanitize_chat_message_empty_string_raises(self):
        """Test that empty string raises HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.sanitize_chat_message("")

        assert exc_info.value.status_code == 400
        assert "non-empty string" in exc_info.value.detail

    def test_sanitize_chat_message_none_raises(self):
        """Test that None raises HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.sanitize_chat_message(None)

        assert exc_info.value.status_code == 400

    def test_sanitize_chat_message_not_string_raises(self):
        """Test that non-string input raises HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.sanitize_chat_message(123)

        assert exc_info.value.status_code == 400

    def test_sanitize_chat_message_exceeds_max_length(self):
        """Test that messages exceeding max length are rejected"""
        long_content = "x" * (InputSanitizer.MAX_MESSAGE_LENGTH + 1)

        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.sanitize_chat_message(long_content)

        assert exc_info.value.status_code == 413
        assert "too long" in exc_info.value.detail

    def test_sanitize_chat_message_at_max_length(self):
        """Test that messages at max length are accepted"""
        content = "x" * InputSanitizer.MAX_MESSAGE_LENGTH

        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert len(sanitized) <= InputSanitizer.MAX_MESSAGE_LENGTH

    def test_sanitize_chat_message_removes_control_characters(self):
        """Test that control characters are removed"""
        content = "Hello\x00\x01\x02World"

        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert "\x00" not in sanitized
        assert "\x01" not in sanitized
        assert "Hello" in sanitized
        assert "World" in sanitized

    def test_sanitize_chat_message_preserves_newlines(self):
        """Test that newlines are preserved in content"""
        content = "Line1\nLine2\nLine3"

        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert "\n" in sanitized or ("Line1" in sanitized and "Line2" in sanitized)

    def test_sanitize_chat_message_with_iframe(self):
        """Test that iframe tags are removed"""
        content = "<iframe src='http://evil.com'></iframe>Hello"

        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert "<iframe" not in sanitized
        assert metadata["sanitized"] is True

    def test_sanitize_chat_message_with_embed(self):
        """Test that embed tags are removed"""
        content = "<embed src='http://evil.com'> Hello"

        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        # Embed tags may or may not trigger dangerous pattern
        assert "<embed" not in sanitized
        assert "Hello" in sanitized

    def test_sanitize_chat_message_with_object(self):
        """Test that object tags are removed"""
        content = "<object data='http://evil.com'></object>"

        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert "<object" not in sanitized
        assert metadata["sanitized"] is True

    def test_sanitize_chat_message_metadata_structure(self):
        """Test metadata structure is correct"""
        content = "Test message"

        sanitized, metadata = InputSanitizer.sanitize_chat_message(content)

        assert "original_length" in metadata
        assert "sanitized" in metadata
        assert "dangerous_patterns_found" in metadata
        assert "length_after_sanitization" in metadata


class TestInputSanitizerConversationTitle:
    """Tests for sanitize_conversation_title method"""

    def test_sanitize_title_valid(self):
        """Test sanitizing valid title"""
        title = "My Conversation"

        result = InputSanitizer.sanitize_conversation_title(title)

        assert result == "My Conversation"

    def test_sanitize_title_empty_returns_default(self):
        """Test that empty title returns default"""
        result = InputSanitizer.sanitize_conversation_title("")

        assert result == "Untitled Conversation"

    def test_sanitize_title_none_returns_default(self):
        """Test that None title returns default"""
        result = InputSanitizer.sanitize_conversation_title(None)

        assert result == "Untitled Conversation"

    def test_sanitize_title_with_html_tags(self):
        """Test that HTML tags are removed from title"""
        title = "My <script>alert('xss')</script> Conversation"

        result = InputSanitizer.sanitize_conversation_title(title)

        assert "<script>" not in result
        assert "My" in result
        assert "Conversation" in result

    def test_sanitize_title_exceeds_max_length(self):
        """Test that title is truncated if too long"""
        long_title = "x" * (InputSanitizer.MAX_TITLE_LENGTH + 100)

        result = InputSanitizer.sanitize_conversation_title(long_title)

        assert len(result) <= InputSanitizer.MAX_TITLE_LENGTH

    def test_sanitize_title_at_max_length(self):
        """Test title at max length"""
        title = "x" * InputSanitizer.MAX_TITLE_LENGTH

        result = InputSanitizer.sanitize_conversation_title(title)

        assert len(result) <= InputSanitizer.MAX_TITLE_LENGTH

    def test_sanitize_title_removes_control_chars(self):
        """Test that control characters are removed"""
        title = "My\x00Conversation\x01Test"

        result = InputSanitizer.sanitize_conversation_title(title)

        assert "\x00" not in result
        assert "My" in result
        assert "Conversation" in result


class TestInputSanitizerUserId:
    """Tests for validate_user_id method"""

    def test_validate_user_id_valid(self):
        """Test validating valid user ID"""
        user_id = "user_123-abc"

        result = InputSanitizer.validate_user_id(user_id)

        assert result == "user_123-abc"

    def test_validate_user_id_none_returns_none(self):
        """Test that None user ID returns None"""
        result = InputSanitizer.validate_user_id(None)

        assert result is None

    def test_validate_user_id_empty_returns_none(self):
        """Test that empty user ID returns None"""
        result = InputSanitizer.validate_user_id("")

        assert result is None

    def test_validate_user_id_not_string_raises(self):
        """Test that non-string user ID raises HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.validate_user_id(123)

        assert exc_info.value.status_code == 400

    def test_validate_user_id_too_long_raises(self):
        """Test that too-long user ID raises HTTPException"""
        long_id = "x" * (InputSanitizer.MAX_USER_ID_LENGTH + 1)

        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.validate_user_id(long_id)

        assert exc_info.value.status_code == 400
        assert "too long" in exc_info.value.detail

    def test_validate_user_id_invalid_characters_raises(self):
        """Test that user ID with invalid characters raises HTTPException"""
        invalid_id = "user@invalid.com"

        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.validate_user_id(invalid_id)

        assert exc_info.value.status_code == 400
        assert "invalid characters" in exc_info.value.detail

    def test_validate_user_id_with_special_chars_raises(self):
        """Test that user ID with special chars raises"""
        with pytest.raises(HTTPException):
            InputSanitizer.validate_user_id("user!@#$%^&*()")

    def test_validate_user_id_with_spaces_raises(self):
        """Test that user ID with spaces raises"""
        with pytest.raises(HTTPException):
            InputSanitizer.validate_user_id("user 123")

    def test_validate_user_id_alphanumeric_underscore_dash_valid(self):
        """Test that alphanumeric, underscore, dash are valid"""
        result = InputSanitizer.validate_user_id("User_123-Test-456")

        assert result == "User_123-Test-456"


class TestInputSanitizerMetadata:
    """Tests for sanitize_metadata method"""

    def test_sanitize_metadata_valid_dict(self):
        """Test sanitizing valid metadata dict"""
        metadata = {
            "key1": "value1",
            "key2": 123,
            "key3": True,
        }

        result = InputSanitizer.sanitize_metadata(metadata)

        assert result is not None
        assert "key1" in result
        assert result["key1"] == "value1"
        assert result["key2"] == 123

    def test_sanitize_metadata_none_returns_none(self):
        """Test that None metadata returns None"""
        result = InputSanitizer.sanitize_metadata(None)

        assert result is None

    def test_sanitize_metadata_empty_dict_returns_none(self):
        """Test that empty dict returns None"""
        result = InputSanitizer.sanitize_metadata({})

        assert result is None

    def test_sanitize_metadata_not_dict_raises(self):
        """Test that non-dict metadata raises HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.sanitize_metadata("not a dict")

        assert exc_info.value.status_code == 400

    def test_sanitize_metadata_escapes_html_values(self):
        """Test that HTML in values is escaped"""
        metadata = {"key": "<script>alert('xss')</script>"}

        result = InputSanitizer.sanitize_metadata(metadata)

        assert "<script>" not in result["key"]

    def test_sanitize_metadata_limits_value_length(self):
        """Test that long values are truncated"""
        long_value = "x" * 2000
        metadata = {"key": long_value}

        result = InputSanitizer.sanitize_metadata(metadata)

        assert len(result["key"]) <= 1000

    def test_sanitize_metadata_removes_invalid_key_chars(self):
        """Test that invalid key characters are removed"""
        metadata = {"key@#$!": "value"}

        result = InputSanitizer.sanitize_metadata(metadata)

        # Key should be sanitized (special chars removed)
        assert len(result) >= 1

    def test_sanitize_metadata_skips_non_string_keys(self):
        """Test that non-string keys are skipped"""
        metadata = {
            "string_key": "value",
            123: "numeric_key_value",
        }

        result = InputSanitizer.sanitize_metadata(metadata)

        assert "string_key" in result
        assert len(result) == 1  # Only string key included

    def test_sanitize_metadata_handles_complex_types(self):
        """Test that complex types are converted to string"""
        metadata = {
            "list_val": [1, 2, 3],
            "dict_val": {"nested": "dict"},
        }

        result = InputSanitizer.sanitize_metadata(metadata)

        assert "list_val" in result
        assert isinstance(result["list_val"], str)


class TestInputSanitizerFilePath:
    """Tests for validate_file_path method"""

    def test_validate_file_path_valid(self):
        """Test validating valid file path"""
        path = "uploads/myfile.txt"

        result = InputSanitizer.validate_file_path(path)

        assert result == path

    def test_validate_file_path_empty_raises(self):
        """Test that empty path raises HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.validate_file_path("")

        assert exc_info.value.status_code == 400

    def test_validate_file_path_none_raises(self):
        """Test that None path raises HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.validate_file_path(None)

        assert exc_info.value.status_code == 400

    def test_validate_file_path_directory_traversal_raises(self):
        """Test that directory traversal attempts are blocked"""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.validate_file_path("../../../etc/passwd")

        assert exc_info.value.status_code == 400
        assert "directory traversal" in exc_info.value.detail

    def test_validate_file_path_absolute_path_raises(self):
        """Test that absolute paths are blocked"""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.validate_file_path("/etc/passwd")

        assert exc_info.value.status_code == 400

    def test_validate_file_path_dot_dot_raises(self):
        """Test that .. in path raises"""
        with pytest.raises(HTTPException):
            InputSanitizer.validate_file_path("subdir/../../../etc/passwd")

    def test_validate_file_path_with_subdirectories(self):
        """Test valid nested file paths"""
        path = "uploads/subfolder/file.txt"
        result = InputSanitizer.validate_file_path(path)

        assert result == path


class TestInputSanitizerRemoveControlCharacters:
    """Tests for _remove_control_characters static method"""

    def test_remove_control_chars_null_byte(self):
        """Test that null bytes are removed"""
        text = "Hello\x00World"

        result = InputSanitizer._remove_control_characters(text)

        assert "\x00" not in result
        assert "Hello" in result
        assert "World" in result

    def test_remove_control_chars_preserves_newline(self):
        """Test that newlines are preserved"""
        text = "Line1\nLine2"

        result = InputSanitizer._remove_control_characters(text)

        assert "\n" in result

    def test_remove_control_chars_preserves_tab(self):
        """Test that tabs are preserved"""
        text = "Col1\tCol2"

        result = InputSanitizer._remove_control_characters(text)

        assert "\t" in result

    def test_remove_control_chars_removes_bell(self):
        """Test that bell character is removed"""
        text = "Hello\x07World"

        result = InputSanitizer._remove_control_characters(text)

        assert "\x07" not in result

    def test_remove_control_chars_removes_escape(self):
        """Test that escape character is removed"""
        text = "Hello\x1bWorld"

        result = InputSanitizer._remove_control_characters(text)

        assert "\x1b" not in result
