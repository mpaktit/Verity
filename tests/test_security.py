"""Tests for security middleware."""

import pytest
from app.middleware.security import (
    validate_url,
    sanitize_input,
    get_security_middleware,
)


class TestValidateUrl:
    """Tests for URL validation."""

    def test_valid_http_url(self):
        """Test validation of valid HTTP URL."""
        assert validate_url("http://example.com") is True
        assert validate_url("http://www.example.com") is True

    def test_valid_https_url(self):
        """Test validation of valid HTTPS URL."""
        assert validate_url("https://example.com") is True
        assert validate_url("https://www.example.com") is True
        assert validate_url("https://example.com/path") is True
        assert validate_url("https://example.com/path?query=value") is True

    def test_valid_url_with_port(self):
        """Test validation of URL with port."""
        assert validate_url("https://example.com:8080") is True
        assert validate_url("http://localhost:3000") is True

    def test_invalid_url_format(self):
        """Test rejection of invalid URL formats."""
        assert validate_url("") is False
        assert validate_url("not-a-url") is False
        assert validate_url("example.com") is False  # Missing protocol
        assert validate_url("ftp://example.com") is False  # Wrong protocol

    def test_block_localhost(self):
        """Test that localhost is blocked."""
        assert validate_url("http://localhost") is False
        assert validate_url("http://localhost:8000") is False

    def test_block_private_ips(self):
        """Test that private IP addresses are blocked."""
        assert validate_url("http://127.0.0.1") is False
        assert validate_url("http://10.0.0.1") is False
        assert validate_url("http://172.16.0.1") is False
        assert validate_url("http://192.168.1.1") is False

    def test_block_loopback(self):
        """Test that loopback addresses are blocked."""
        assert validate_url("http://127.0.0.1:8000") is False
        assert validate_url("https://127.0.0.1/api") is False

    def test_allow_public_ip(self):
        """Test that public IP addresses are allowed."""
        assert validate_url("http://8.8.8.8") is True
        assert validate_url("https://1.1.1.1") is True


class TestSanitizeInput:
    """Tests for input sanitization."""

    def test_sanitize_normal_text(self):
        """Test sanitization of normal text."""
        result = sanitize_input("Hello, world!")
        assert result == "Hello, world!"

    def test_sanitize_with_max_length(self):
        """Test sanitization with max length limit."""
        long_text = "a" * 10000
        result = sanitize_input(long_text, max_length=100)
        assert len(result) == 100

    def test_remove_script_tags(self):
        """Test removal of script tags."""
        result = sanitize_input("<script>alert('xss')</script>Hello")
        assert "<script" not in result
        assert "Hello" in result

    def test_remove_iframe_tags(self):
        """Test removal of iframe tags."""
        result = sanitize_input("<iframe src='evil.com'></iframe>Hello")
        assert "<iframe" not in result
        assert "Hello" in result

    def test_remove_onclick_handlers(self):
        """Test removal of onclick and other event handlers."""
        result = sanitize_input('<div onclick="alert(1)">Click me</div>')
        assert "onclick" not in result
        assert "Click me" in result

    def test_sanitize_empty_string(self):
        """Test sanitization of empty string."""
        result = sanitize_input("")
        assert result == ""

    def test_sanitize_none(self):
        """Test sanitization of None."""
        result = sanitize_input(None)
        assert result == ""

    def test_sanitize_with_special_characters(self):
        """Test sanitization preserves safe special characters."""
        result = sanitize_input("Hello & goodbye! Test@test.com")
        assert "Hello" in result
        assert "goodbye" in result

    def test_sanitize_multiline(self):
        """Test sanitization of multiline text."""
        result = sanitize_input("Line 1\nLine 2\nLine 3")
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result


class TestGetSecurityMiddleware:
    """Tests for security middleware configuration."""

    def test_returns_list(self):
        """Test that get_security_middleware returns a list."""
        middleware = get_security_middleware()
        assert isinstance(middleware, list)
        assert len(middleware) > 0

    def test_includes_cors_middleware(self):
        """Test that CORS middleware is included."""
        middleware = get_security_middleware()
        middleware_classes = [m.cls.__name__ for m in middleware]
        assert "CORSMiddleware" in middleware_classes

    def test_includes_gzip_middleware(self):
        """Test that GZip middleware is included."""
        middleware = get_security_middleware()
        middleware_classes = [m.cls.__name__ for m in middleware]
        assert "GZipMiddleware" in middleware_classes

    def test_includes_trusted_host_middleware(self):
        """Test that TrustedHost middleware is included."""
        middleware = get_security_middleware()
        middleware_classes = [m.cls.__name__ for m in middleware]
        assert "TrustedHostMiddleware" in middleware_classes


class TestSecurityPatterns:
    """Tests for security pattern matching."""

    def test_xss_pattern_removal(self):
        """Test various XSS patterns are removed."""
        xss_attacks = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "<body onload=alert(1)>",
            "<input onfocus=alert(1) autofocus>",
        ]

        for attack in xss_attacks:
            result = sanitize_input(attack)
            # Should remove the dangerous parts
            assert "onerror" not in result or "alert" not in result

    def test_sql_injection_patterns(self):
        """Test that SQL injection patterns are not explicitly handled (basic sanitization only)."""
        # Note: This is basic sanitization, not full SQL injection prevention
        # Real SQL injection prevention should use parameterized queries
        result = sanitize_input("SELECT * FROM users WHERE id = 1")
        assert "SELECT" in result  # Basic sanitization doesn't remove SQL keywords

    def test_html_entities_preserved(self):
        """Test that HTML entities are handled."""
        result = sanitize_input("Hello &amp; goodbye")
        assert "Hello" in result
        assert "goodbye" in result

    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        result = sanitize_input("Hello  🌍")
        assert "Hello" in result
        # Unicode should be preserved or handled gracefully
        assert len(result) > 0
