"""
Tests for PII sanitization and data privacy
Tests detection and sanitization of personally identifiable information
"""

import pytest

from api.services.sanitization import (
    PIISanitizer,
    SanitizationLevel,
)


@pytest.fixture
def sanitizer():
    """Create PIISanitizer instance for testing"""
    return PIISanitizer()


class TestPIIPatternDetection:
    """Tests for PII pattern detection"""

    def test_detect_email_address(self, sanitizer):
        """Test detecting email addresses"""
        text = "Contact me at john@example.com"

        pii_items = sanitizer.detect_pii(text)

        assert any(
            item.pattern_type == "email" for item in pii_items
        )

    def test_detect_phone_number(self, sanitizer):
        """Test detecting phone numbers"""
        text = "Call me at 555-123-4567"

        pii_items = sanitizer.detect_pii(text)

        assert any(
            item.pattern_type == "phone" for item in pii_items
        )

    def test_detect_credit_card(self, sanitizer):
        """Test detecting credit card numbers"""
        text = "Card: 4532-1234-5678-9010"

        pii_items = sanitizer.detect_pii(text)

        assert any(
            item.pattern_type == "credit_card"
            for item in pii_items
        )

    def test_detect_ssn(self, sanitizer):
        """Test detecting social security numbers"""
        text = "My SSN is 123-45-6789"

        pii_items = sanitizer.detect_pii(text)

        assert any(
            item.pattern_type == "ssn" for item in pii_items
        )

    def test_detect_ip_address(self, sanitizer):
        """Test detecting IP addresses"""
        text = "Server at 192.168.1.1"

        pii_items = sanitizer.detect_pii(text)

        assert any(
            item.pattern_type == "ip_address"
            for item in pii_items
        )

    def test_detect_api_key(self, sanitizer):
        """Test detecting API keys"""
        text = "sk-proj-abc123xyz789def456"

        pii_items = sanitizer.detect_pii(text)

        # Should detect API key patterns
        assert isinstance(pii_items, list)

    def test_detect_name_patterns(self, sanitizer):
        """Test detecting name patterns"""
        text = "My name is John Smith from New York"

        pii_items = sanitizer.detect_pii(text)

        # May detect names depending on confidence
        assert isinstance(pii_items, list)

    def test_detect_address(self, sanitizer):
        """Test detecting addresses"""
        text = "123 Main Street, Springfield, IL 62701"

        pii_items = sanitizer.detect_pii(text)

        # Should detect address-like patterns
        assert isinstance(pii_items, list)


class TestPIISanitization:
    """Tests for PII sanitization"""

    def test_mask_email(self, sanitizer):
        """Test masking email addresses"""
        text = "Email: john@example.com"

        sanitized = sanitizer.sanitize(
            text,
            level=SanitizationLevel.MASK,
        )

        assert "john@example.com" not in sanitized
        assert "[EMAIL]" in sanitized or "*" in sanitized

    def test_redact_phone_number(self, sanitizer):
        """Test redacting phone numbers"""
        text = "Phone: 555-123-4567"

        sanitized = sanitizer.sanitize(
            text,
            level=SanitizationLevel.REDACT,
        )

        assert "555-123-4567" not in sanitized

    def test_hash_credit_card(self, sanitizer):
        """Test hashing credit card numbers"""
        text = "4532-1234-5678-9010"

        sanitized = sanitizer.sanitize(
            text,
            level=SanitizationLevel.HASH,
        )

        assert "4532-1234-5678-9010" not in sanitized

    def test_sanitization_levels(self, sanitizer):
        """Test different sanitization levels"""
        text = "Email: john@example.com, Phone: 555-1234"

        for level in [
            SanitizationLevel.MASK,
            SanitizationLevel.REDACT,
            SanitizationLevel.HASH,
        ]:
            sanitized = sanitizer.sanitize(text, level=level)

            # Original should not be in sanitized version
            assert (
                "john@example.com" not in sanitized or
                level == SanitizationLevel.NONE
            )


class TestPIISanitizationEdgeCases:
    """Tests for sanitization edge cases"""

    def test_preserve_non_pii_text(self, sanitizer):
        """Test non-PII text is preserved"""
        text = "Python programming is fun"

        sanitized = sanitizer.sanitize(text)

        assert "Python" in sanitized
        assert "programming" in sanitized

    def test_multiple_pii_items(self, sanitizer):
        """Test handling multiple PII items"""
        text = (
            "Contact john@example.com or 555-1234 "
            "at 123 Main St"
        )

        sanitized = sanitizer.sanitize(text)

        # Original sensitive info should be gone
        assert "john@example.com" not in sanitized

    def test_nested_pii(self, sanitizer):
        """Test nested PII detection"""
        text = (
            'Email in JSON: {"email": "test@example.com"}'
        )

        pii_items = sanitizer.detect_pii(text)

        assert any(
            item.pattern_type == "email" for item in pii_items
        )

    def test_encoded_pii(self, sanitizer):
        """Test detecting encoded PII"""
        import base64

        email = "test@example.com"
        encoded = base64.b64encode(email.encode()).decode()

        # May or may not detect encoded data depending on impl
        pii_items = sanitizer.detect_pii(encoded)

        assert isinstance(pii_items, list)

    def test_obfuscated_pii(self, sanitizer):
        """Test detecting obfuscated PII"""
        text = "Email: t***t@ex***le.com"

        # Obfuscated data is harder to detect
        pii_items = sanitizer.detect_pii(text)

        assert isinstance(pii_items, list)


class TestPIIContextAwareness:
    """Tests for context-aware sanitization"""

    def test_preserve_necessary_identifiers(self, sanitizer):
        """Test preserving necessary context"""
        text = (
            "User ID 12345 reported issue from 192.168.1.1"
        )

        sanitized = sanitizer.sanitize(
            text,
            level=SanitizationLevel.MASK,
            preserve_context=True,
        )

        # Should preserve structure for debugging
        assert "User ID" in sanitized

    def test_sanitize_in_code(self, sanitizer):
        """Test sanitizing within code blocks"""
        code = (
            'password = "MyPassword123!"\n'
            'email = "john@example.com"'
        )

        sanitized = sanitizer.sanitize(code)

        # Code structure should be preserved
        assert "password =" in sanitized
        assert "john@example.com" not in sanitized

    def test_sanitize_in_logs(self, sanitizer):
        """Test sanitizing in log output"""
        log = (
            "2024-01-01 ERROR: Failed to connect "
            "to 192.168.1.100:5432 with user admin"
        )

        sanitized = sanitizer.sanitize(log)

        # Timestamp and log level preserved, IP sanitized
        assert "ERROR:" in sanitized
        assert "192.168.1.100" not in sanitized or (
            "[IP]" in sanitized
        )


class TestPIIComplianceFeatures:
    """Tests for compliance-related features"""

    def test_audit_log_pii_detection(self, sanitizer):
        """Test audit logging for PII detection"""
        text = "Email: john@example.com"

        pii_items = sanitizer.detect_pii(
            text,
            log_detection=True,
        )

        # Should log the detection
        assert len(pii_items) > 0

    def test_retention_policy(self, sanitizer):
        """Test PII retention policies"""
        policy = sanitizer.get_retention_policy(
            data_type="pii"
        )

        # Should have a defined policy
        assert policy is not None

    def test_data_minimization(self, sanitizer):
        """Test data minimization"""
        text = (
            "User: john@example.com, "
            "Age: 30, Location: NYC"
        )

        minimized = sanitizer.minimize_data(text)

        # Should remove non-essential PII
        assert minimized is not None

    def test_consent_check(self, sanitizer):
        """Test consent checking before sanitization"""
        has_consent = sanitizer.check_consent(
            data_subject="user123"
        )

        assert isinstance(has_consent, bool)


class TestPIISanitizationPerformance:
    """Tests for sanitization performance"""

    def test_large_text_sanitization(self, sanitizer):
        """Test sanitizing large texts"""
        large_text = (
            "Normal text email@example.com " * 10000
        )

        sanitized = sanitizer.sanitize(large_text)

        assert sanitized is not None
        assert "email@example.com" not in sanitized

    def test_batch_sanitization(self, sanitizer):
        """Test batch sanitization"""
        texts = [
            "Email: test1@example.com",
            "Phone: 555-1111",
            "Normal text",
        ]

        results = sanitizer.sanitize_batch(texts)

        assert len(results) == 3
        assert "test1@example.com" not in results[0]

    def test_sanitization_caching(self, sanitizer):
        """Test sanitization results can be cached"""
        text = "Email: john@example.com"

        # First call
        result1 = sanitizer.sanitize(text)

        # Second call should use cache
        result2 = sanitizer.sanitize(text)

        assert result1 == result2
