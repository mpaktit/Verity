"""Web scraping service with platform-specific integrations and rate limiting."""

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
import feedparser
from bs4 import BeautifulSoup

from app.config import settings


class Platform(Enum):
    REDDIT = "reddit"
    GITHUB = "github"
    TWITTER = "twitter"
    X = "x"
    PRODUCT_HUNT = "producthunt"
    HACKER_NEWS = "hackernews"
    LINKEDIN = "linkedin"
    INDIE_HACKERS = "indiehackers"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    GENERIC = "generic"


@dataclass
class ScrapedContent:
    platform: Platform
    url: str
    title: str
    content: str
    metadata: dict
    author: Optional[str] = None
    published_at: Optional[str] = None
    score: Optional[int] = None
    tags: list[str] = None
    extracted_at: str = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.extracted_at is None:
            self.extracted_at = datetime.now(timezone.utc).isoformat()


class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until a request is allowed."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            # Remove requests older than 1 minute
            self.requests = [r for r in self.requests if (now - r).total_seconds() < 60]

            if len(self.requests) >= self.requests_per_minute:
                wait_time = 60 - (now - self.requests[0]).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            self.requests.append(now)


class WebScraper:
    """Service for scraping content from various platforms."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
        )
        self.rate_limiters = {
            Platform.REDDIT: RateLimiter(30),
            Platform.GITHUB: RateLimiter(60),
            Platform.TWITTER: RateLimiter(15),
            Platform.PRODUCT_HUNT: RateLimiter(30),
            Platform.HACKER_NEWS: RateLimiter(30),
            Platform.GENERIC: RateLimiter(60),
        }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def scrape_url(self, url: str) -> Optional[ScrapedContent]:
        """Scrape a generic URL."""
        platform = self._detect_platform(url)
        await self.rate_limiters[platform].acquire()

        try:
            if platform == Platform.REDDIT:
                return await self._scrape_reddit(url)
            elif platform == Platform.GITHUB:
                return await self._scrape_github(url)
            elif platform == Platform.HACKER_NEWS:
                return await self._scrape_hackernews(url)
            else:
                return await self._scrape_generic(url)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

    def _detect_platform(self, url: str) -> Platform:
        """Detect the platform from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if "reddit.com" in domain:
            return Platform.REDDIT
        elif "github.com" in domain:
            return Platform.GITHUB
        elif "twitter.com" in domain or "x.com" in domain:
            return Platform.X
        elif "producthunt.com" in domain:
            return Platform.PRODUCT_HUNT
        elif "news.ycombinator.com" in domain:
            return Platform.HACKER_NEWS
        elif "linkedin.com" in domain:
            return Platform.LINKEDIN
        elif "indiehackers.com" in domain:
            return Platform.INDIE_HACKERS
        else:
            return Platform.GENERIC

    async def _scrape_generic(self, url: str) -> Optional[ScrapedContent]:
        """Scrape a generic webpage."""
        response = await self.client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Extract title
        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else ""

        # Extract main content
        content_selectors = [
            "main",
            "article",
            '[role="main"]',
            ".content",
            "#content",
            ".post-content",
            ".entry-content",
        ]

        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break

        if not content_element:
            content_element = soup.body

        # Remove scripts and styles
        for element in content_element(["script", "style", "noscript"]):
            element.decompose()

        content_text = content_element.get_text(separator="\n", strip=True)

        # Extract metadata
        metadata = {
            "meta_description": soup.find("meta", attrs={"name": "description"})?.get("content"),
            "meta_keywords": soup.find("meta", attrs={"name": "keywords"})?.get("content"),
            "og_title": soup.find("meta", property="og:title")?.get("content"),
            "og_description": soup.find("meta", property="og:description")?.get("content"),
            "canonical": soup.find("link", rel="canonical")?.get("href"),
            "h1": soup.find("h1")?.get_text(strip=True),
            "h2_count": len(soup.find_all("h2")),
            "link_count": len(soup.find_all("a")),
        }

        return ScrapedContent(
            platform=Platform.GENERIC,
            url=url,
            title=title_text,
            content=content_text[:10000],  # Limit content
            metadata=metadata,
        )

    async def _scrape_reddit(self, url: str) -> Optional[ScrapedContent]:
        """Scrape a Reddit post or thread."""
        # Reddit API requires OAuth, so we'll use the public JSON endpoint
        if ".json" not in url:
            url = url.rstrip("/") + ".json"

        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            return None

        post_data = data[0]["data"]["children"][0]["data"]

        title = post_data.get("title", "")
        content = post_data.get("selftext", "")
        author = post_data.get("author")
        score = post_data.get("score")
        created_utc = post_data.get("created_utc")

        published_at = None
        if created_utc:
            published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()

        metadata = {
            "subreddit": post_data.get("subreddit"),
            "upvote_ratio": post_data.get("upvote_ratio"),
            "num_comments": post_data.get("num_comments"),
            "is_self": post_data.get("is_self"),
        }

        return ScrapedContent(
            platform=Platform.REDDIT,
            url=url,
            title=title,
            content=content[:10000],
            metadata=metadata,
            author=author,
            published_at=published_at,
            score=score,
        )

    async def _scrape_github(self, url: str) -> Optional[ScrapedContent]:
        """Scrape a GitHub repository or issue."""
        response = await self.client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Extract title based on page type
        if "/issues/" in url:
            title_element = soup.find("span", class_="js-issue-title")
            title = title_element.get_text(strip=True) if title_element else ""
        else:
            title_element = soup.find("h1", class_="d-flex")
            title = title_element.get_text(strip=True) if title_element else ""

        # Extract content
        content_element = soup.find("div", class_="markdown-body")
        if not content_element:
            content_element = soup.find("div", class_="Box-body")

        content = content_element.get_text(separator="\n", strip=True) if content_element else ""

        # Extract metadata
        metadata = {
            "stars": soup.select_one(".social-count")?.get_text(strip=True),
            "forks": soup.select_one('a[href*="network/members"]')?.get_text(strip=True),
            "language": soup.select_one(".lang")?.get_text(strip=True),
            "open_issues": soup.select_one('a[href*="issues"]')?.get_text(strip=True),
        }

        return ScrapedContent(
            platform=Platform.GITHUB,
            url=url,
            title=title,
            content=content[:10000],
            metadata=metadata,
        )

    async def _scrape_hackernews(self, url: str) -> Optional[ScrapedContent]:
        """Scrape a Hacker News post."""
        # Extract item ID from URL
        match = re.search(r"id=(\d+)", url)
        if not match:
            return None

        item_id = match.group(1)
        api_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

        response = await self.client.get(api_url)
        response.raise_for_status()
        data = response.json()

        title = data.get("title", "")
        content = data.get("text", "")
        author = data.get("by")
        score = data.get("score")
        created_time = data.get("time")

        published_at = None
        if created_time:
            published_at = datetime.fromtimestamp(created_time, tz=timezone.utc).isoformat()

        metadata = {
            "descendants": data.get("descendants"),
            "url": data.get("url"),
            "type": data.get("type"),
        }

        return ScrapedContent(
            platform=Platform.HACKER_NEWS,
            url=url,
            title=title,
            content=content[:10000],
            metadata=metadata,
            author=author,
            published_at=published_at,
            score=score,
        )

    async def search_platform(
        self,
        platform: Platform,
        query: str,
        limit: int = 10,
    ) -> list[ScrapedContent]:
        """Search a platform for content matching a query."""
        results = []

        if platform == Platform.HACKER_NEWS:
            results = await self._search_hackernews(query, limit)
        elif platform == Platform.REDDIT:
            results = await self._search_reddit(query, limit)
        elif platform == Platform.GITHUB:
            results = await self._search_github(query, limit)

        return results

    async def _search_hackernews(self, query: str, limit: int) -> list[ScrapedContent]:
        """Search Hacker News via Algolia API."""
        search_url = "http://hn.algolia.com/api/v1/search"
        params = {"query": query, "hitsPerPage": limit}

        response = await self.client.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        for hit in data.get("hits", []):
            title = hit.get("title", "")
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            author = hit.get("author")
            score = hit.get("points")
            created_at = hit.get("created_at")

            metadata = {
                "objectID": hit.get("objectID"),
                "num_comments": hit.get("num_comments"),
            }

            results.append(
                ScrapedContent(
                    platform=Platform.HACKER_NEWS,
                    url=url,
                    title=title,
                    content="",  # HN search doesn't return full content
                    metadata=metadata,
                    author=author,
                    score=score,
                    published_at=created_at,
                )
            )

        return results

    async def _search_reddit(self, query: str, limit: int) -> list[ScrapedContent]:
        """Search Reddit (requires OAuth for full functionality, this is a basic version)."""
        # Note: Reddit search requires OAuth for production use
        # This is a placeholder for the implementation
        search_url = "https://www.reddit.com/search.json"
        params = {"q": query, "limit": limit, "sort": "relevance"}

        try:
            response = await self.client.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for child in data.get("data", {}).get("children", [])[:limit]:
                post = child.get("data", {})
                title = post.get("title", "")
                permalink = post.get("permalink", "")
                url = f"https://www.reddit.com{permalink}"
                author = post.get("author")
                score = post.get("score")

                results.append(
                    ScrapedContent(
                        platform=Platform.REDDIT,
                        url=url,
                        title=title,
                        content=post.get("selftext", "")[:10000],
                        metadata={"subreddit": post.get("subreddit")},
                        author=author,
                        score=score,
                    )
                )

            return results
        except Exception as e:
            print(f"Reddit search error: {e}")
            return []

    async def _search_github(self, query: str, limit: int) -> list[ScrapedContent]:
        """Search GitHub repositories."""
        search_url = "https://api.github.com/search/repositories"
        params = {"q": query, "per_page": limit, "sort": "stars"}

        response = await self.client.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("items", []):
            title = item.get("name", "")
            url = item.get("html_url", "")
            description = item.get("description", "")
            author = item.get("owner", {}).get("login")
            score = item.get("stargazers_count")
            created_at = item.get("created_at")

            metadata = {
                "language": item.get("language"),
                "forks": item.get("forks_count"),
                "open_issues": item.get("open_issues_count"),
                "updated_at": item.get("updated_at"),
            }

            results.append(
                ScrapedContent(
                    platform=Platform.GITHUB,
                    url=url,
                    title=title,
                    content=description[:10000],
                    metadata=metadata,
                    author=author,
                    score=score,
                    published_at=created_at,
                )
            )

        return results

    async def fetch_rss_feed(self, feed_url: str) -> list[ScrapedContent]:
        """Fetch and parse an RSS feed."""
        response = await self.client.get(feed_url)
        response.raise_for_status()

        feed = feedparser.parse(response.text)
        results = []

        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            url = entry.get("link", "")
            content = entry.get("description", "") or entry.get("summary", "")
            author = entry.get("author")
            published_at = entry.get("published")

            metadata = {
                "tags": [tag.get("term") for tag in entry.get("tags", [])],
                "feed_title": feed.get("feed", {}).get("title"),
            }

            results.append(
                ScrapedContent(
                    platform=Platform.GENERIC,
                    url=url,
                    title=title,
                    content=content[:10000],
                    metadata=metadata,
                    author=author,
                    published_at=published_at,
                    tags=[tag.get("term") for tag in entry.get("tags", [])],
                )
            )

        return results


# Global instance
_scraper: Optional[WebScraper] = None


def get_scraper() -> WebScraper:
    """Get or create the global scraper instance."""
    global _scraper
    if _scraper is None:
        _scraper = WebScraper()
    return _scraper
