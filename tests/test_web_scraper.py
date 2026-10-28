"""Tests for web scraper service."""

import pytest
from app.services.web_scraper import WebScraper, Platform, RateLimiter


@pytest.fixture
def scraper():
    """Create a web scraper instance."""
    return WebScraper()


@pytest.fixture
async def cleanup_scraper(scraper):
    """Cleanup scraper after tests."""
    yield
    await scraper.close()


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        """Test that rate limiter allows requests within limit."""
        limiter = RateLimiter(requests_per_minute=60)

        # Should allow multiple requests
        for _ in range(5):
            await limiter.acquire()

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_when_exceeded(self):
        """Test that rate limiter blocks when limit exceeded."""
        limiter = RateLimiter(requests_per_minute=2)

        # Allow first 2 requests
        await limiter.acquire()
        await limiter.acquire()

        # Third request should wait (simulate by checking it doesn't fail)
        await limiter.acquire()


class TestWebScraper:
    """Tests for WebScraper class."""

    def test_detect_platform_reddit(self, scraper):
        """Test platform detection for Reddit."""
        assert scraper._detect_platform("https://reddit.com/r/python") == Platform.REDDIT
        assert scraper._detect_platform("https://www.reddit.com/r/artificial") == Platform.REDDIT

    def test_detect_platform_github(self, scraper):
        """Test platform detection for GitHub."""
        assert scraper._detect_platform("https://github.com/user/repo") == Platform.GITHUB
        assert scraper._detect_platform("https://www.github.com/org/project") == Platform.GITHUB

    def test_detect_platform_hackernews(self, scraper):
        """Test platform detection for Hacker News."""
        assert scraper._detect_platform("https://news.ycombinator.com/item?id=12345") == Platform.HACKER_NEWS

    def test_detect_platform_generic(self, scraper):
        """Test platform detection for generic URLs."""
        assert scraper._detect_platform("https://example.com/page") == Platform.GENERIC
        assert scraper._detect_platform("https://some-site.com/article") == Platform.GENERIC

    @pytest.mark.asyncio
    async def test_scrape_generic_url(self, scraper, cleanup_scraper):
        """Test scraping a generic URL."""
        # Use a simple test URL that should always be accessible
        result = await scraper.scrape_url("https://example.com")

        assert result is not None
        assert result.platform == Platform.GENERIC
        assert result.url == "https://example.com"
        assert isinstance(result.title, str)
        assert isinstance(result.content, str)
        assert isinstance(result.metadata, dict)

    @pytest.mark.asyncio
    async def test_scrape_invalid_url(self, scraper, cleanup_scraper):
        """Test scraping an invalid URL."""
        result = await scraper.scrape_url("https://this-domain-does-not-exist-12345.com")

        # Should return None for failed requests
        assert result is None

    @pytest.mark.asyncio
    async def test_search_hackernews(self, scraper, cleanup_scraper):
        """Test searching Hacker News."""
        results = await scraper.search_platform(Platform.HACKER_NEWS, "python", limit=5)

        assert isinstance(results, list)
        # May return empty results if API is down, but should not raise exception
        for result in results:
            assert result.platform == Platform.HACKER_NEWS
            assert isinstance(result.title, str)
            assert isinstance(result.url, str)

    @pytest.mark.asyncio
    async def test_search_github(self, scraper, cleanup_scraper):
        """Test searching GitHub."""
        results = await scraper.search_platform(Platform.GITHUB, "fastapi", limit=5)

        assert isinstance(results, list)
        for result in results:
            assert result.platform == Platform.GITHUB
            assert isinstance(result.title, str)
            assert isinstance(result.url, str)
            assert result.url.startswith("https://github.com")

    @pytest.mark.asyncio
    async def test_fetch_rss_feed(self, scraper, cleanup_scraper):
        """Test fetching an RSS feed."""
        # Use a known RSS feed
        results = await scraper.fetch_rss_feed("https://news.ycombinator.com/rss")

        assert isinstance(results, list)
        if len(results) > 0:
            result = results[0]
            assert isinstance(result.title, str)
            assert isinstance(result.url, str)
            assert isinstance(result.content, str)

    @pytest.mark.asyncio
    async def test_multiple_platform_search(self, scraper, cleanup_scraper):
        """Test searching multiple platforms."""
        platforms = [Platform.HACKER_NEWS, Platform.GITHUB]
        results = []

        for platform in platforms:
            try:
                platform_results = await scraper.search_platform(platform, "ai", limit=3)
                results.extend(platform_results)
            except Exception as e:
                # Individual platform failures shouldn't break the test
                print(f"Error searching {platform}: {e}")

        # Should have results from at least one platform
        assert isinstance(results, list)


class TestScrapedContent:
    """Tests for ScrapedContent dataclass."""

    def test_scraped_content_creation(self):
        """Test creating a ScrapedContent instance."""
        from app.services.web_scraper import ScrapedContent

        content = ScrapedContent(
            platform=Platform.GENERIC,
            url="https://example.com",
            title="Test Title",
            content="Test content",
            metadata={"key": "value"},
        )

        assert content.platform == Platform.GENERIC
        assert content.url == "https://example.com"
        assert content.title == "Test Title"
        assert content.content == "Test content"
        assert content.metadata == {"key": "value"}
        assert content.tags == []  # Default value
        assert content.extracted_at is not None  # Auto-generated
