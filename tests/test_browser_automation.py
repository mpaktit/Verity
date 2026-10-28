"""Tests for browser automation service."""

import pytest
from app.services.browser_automation import (
    BrowserAutomationService,
    BrowserType,
    VerificationResult,
)


@pytest.fixture
def browser_service():
    """Create a browser automation service instance."""
    return BrowserAutomationService(headless=True, browser_type=BrowserType.CHROMIUM)


@pytest.fixture
async def cleanup_browser(browser_service):
    """Cleanup browser service after tests."""
    yield
    await browser_service.close()


class TestBrowserAutomationService:
    """Tests for BrowserAutomationService class."""

    @pytest.mark.asyncio
    async def test_initialize_browser(self, browser_service, cleanup_browser):
        """Test browser initialization."""
        assert not browser_service._initialized

        await browser_service.initialize()

        assert browser_service._initialized
        assert browser_service.browser is not None
        assert browser_service.context is not None

    @pytest.mark.asyncio
    async def test_close_browser(self, browser_service, cleanup_browser):
        """Test browser cleanup."""
        await browser_service.initialize()
        assert browser_service._initialized

        await browser_service.close()

        assert not browser_service._initialized

    @pytest.mark.asyncio
    async def test_verify_url(self, browser_service, cleanup_browser):
        """Test URL verification."""
        await browser_service.initialize()

        result = await browser_service.verify_url(
            url="https://example.com",
            screenshot=False,
        )

        assert isinstance(result, VerificationResult)
        assert result.url == "https://example.com"
        assert result.success is True
        assert result.status_code == 200
        assert result.title is not None
        assert isinstance(result.content, str)
        assert isinstance(result.metadata, dict)
        assert result.error is None

    @pytest.mark.asyncio
    async def test_verify_url_with_screenshot(self, browser_service, cleanup_browser):
        """Test URL verification with screenshot."""
        await browser_service.initialize()

        result = await browser_service.verify_url(
            url="https://example.com",
            screenshot=True,
        )

        assert result.success is True
        assert result.screenshot is not None
        assert isinstance(result.screenshot, str)
        # Screenshot should be base64 encoded
        assert len(result.screenshot) > 0

    @pytest.mark.asyncio
    async def test_verify_invalid_url(self, browser_service, cleanup_browser):
        """Test verification of invalid URL."""
        await browser_service.initialize()

        result = await browser_service.verify_url(
            url="https://this-domain-does-not-exist-12345.com",
            screenshot=False,
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_extract_forms(self, browser_service, cleanup_browser):
        """Test form extraction from a page."""
        await browser_service.initialize()

        forms = await browser_service.extract_forms("https://example.com")

        assert isinstance(forms, list)
        # example.com might not have forms, but should not crash
        for form in forms:
            assert "action" in form
            assert "method" in form
            assert "input_count" in form
            assert "inputs" in form

    @pytest.mark.asyncio
    async def test_check_eligibility_page(self, browser_service, cleanup_browser):
        """Test eligibility checking."""
        await browser_service.initialize()

        result = await browser_service.check_eligibility_page(
            url="https://example.com",
            keywords=["test", "example"],
        )

        assert isinstance(result, dict)
        assert "eligible" in result
        assert "found_keywords" in result
        assert "keyword_count" in result
        assert isinstance(result["eligible"], bool)
        assert isinstance(result["found_keywords"], list)
        assert isinstance(result["keyword_count"], int)

    @pytest.mark.asyncio
    async def test_check_signup_flow(self, browser_service, cleanup_browser):
        """Test signup flow analysis."""
        await browser_service.initialize()

        result = await browser_service.check_signup_flow("https://example.com")

        assert isinstance(result, dict)
        assert "steps" in result
        assert "success" in result
        assert "signup_detected" in result
        assert isinstance(result["steps"], list)
        assert isinstance(result["success"], bool)
        assert isinstance(result["signup_detected"], bool)


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_verification_result_creation(self):
        """Test creating a VerificationResult."""
        result = VerificationResult(
            success=True,
            url="https://example.com",
            status_code=200,
            title="Example Domain",
            content="Example content",
            screenshot=None,
            metadata={"test": "data"},
        )

        assert result.success is True
        assert result.url == "https://example.com"
        assert result.status_code == 200
        assert result.title == "Example Domain"
        assert result.content == "Example content"
        assert result.metadata == {"test": "data"}
        assert result.timestamp is not None  # Auto-generated

    def test_verification_result_with_error(self):
        """Test VerificationResult with error."""
        result = VerificationResult(
            success=False,
            url="https://example.com",
            status_code=None,
            title=None,
            content=None,
            screenshot=None,
            metadata={},
            error="Connection failed",
        )

        assert result.success is False
        assert result.error == "Connection failed"


class TestBrowserType:
    """Tests for BrowserType enum."""

    def test_browser_type_values(self):
        """Test BrowserType enum values."""
        assert BrowserType.CHROMIUM.value == "chromium"
        assert BrowserType.FIREFOX.value == "firefox"
        assert BrowserType.WEBKIT.value == "webkit"


@pytest.mark.integration
class TestBrowserAutomationIntegration:
    """Integration tests for browser automation (may be slow)."""

    @pytest.mark.asyncio
    async def test_real_world_verification(self, browser_service, cleanup_browser):
        """Test verification of a real website."""
        await browser_service.initialize()

        # Test with a real site that should be accessible
        result = await browser_service.verify_url(
            url="https://httpbin.org/html",
            screenshot=False,
        )

        assert result.success is True
        assert result.status_code == 200
        assert "httpbin" in result.title.lower() or "http" in result.title.lower()

    @pytest.mark.asyncio
    async def test_content_extraction(self, browser_service, cleanup_browser):
        """Test content extraction from real page."""
        await browser_service.initialize()

        result = await browser_service.verify_url(
            url="https://example.com",
            screenshot=False,
        )

        assert result.content is not None
        assert len(result.content) > 0
        # Content should have some text
        assert len(result.content.strip()) > 0

    @pytest.mark.asyncio
    async def test_metadata_extraction(self, browser_service, cleanup_browser):
        """Test metadata extraction from real page."""
        await browser_service.initialize()

        result = await browser_service.verify_url(
            url="https://example.com",
            screenshot=False,
        )

        assert result.metadata is not None
        assert isinstance(result.metadata, dict)
        # Check for common metadata fields
        assert "h1" in result.metadata or "meta_description" in result.metadata
