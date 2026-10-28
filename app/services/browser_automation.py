"""Browser automation service for platform verification using Playwright."""

import asyncio
import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser, Page, BrowserContext


class BrowserType(Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


@dataclass
class VerificationResult:
    success: bool
    url: str
    status_code: Optional[int]
    title: Optional[str]
    content: Optional[str]
    screenshot: Optional[str]  # base64 encoded
    metadata: dict
    error: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class BrowserAutomationService:
    """Service for automated browser interactions and platform verification."""

    def __init__(self, headless: bool = True, browser_type: BrowserType = BrowserType.CHROMIUM):
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the browser instance."""
        if self._initialized:
            return

        self.playwright = await async_playwright().start()
        launch_options = {
            "headless": self.headless,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        }

        if self.browser_type == BrowserType.CHROMIUM:
            self.browser = await self.playwright.chromium.launch(**launch_options)
        elif self.browser_type == BrowserType.FIREFOX:
            self.browser = await self.playwright.firefox.launch(**launch_options)
        else:
            self.browser = await self.playwright.webkit.launch(**launch_options)

        # Create context with realistic user agent
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )

        self._initialized = True

    async def close(self):
        """Close the browser and cleanup resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self._initialized = False

    async def verify_url(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        timeout: int = 30000,
        screenshot: bool = True,
    ) -> VerificationResult:
        """Verify a URL and extract content."""
        if not self._initialized:
            await self.initialize()

        page = await self.context.new_page()
        result = VerificationResult(
            success=False,
            url=url,
            status_code=None,
            title=None,
            content=None,
            screenshot=None,
            metadata={},
        )

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            result.status_code = response.status if response else None

            # Wait for specific selector if provided
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=timeout)

            # Extract page title
            result.title = await page.title()

            # Extract main content
            content = await page.evaluate("""
                () => {
                    // Remove script and style elements
                    const scripts = document.querySelectorAll('script, style, noscript');
                    scripts.forEach(el => el.remove());

                    // Get main content areas
                    const main = document.querySelector('main') ||
                               document.querySelector('[role="main"]') ||
                               document.querySelector('.content') ||
                               document.querySelector('#content') ||
                               document.body;

                    return main ? main.innerText : document.body.innerText;
                }
            """)
            result.content = content[:10000] if content else None  # Limit content size

            # Take screenshot if requested
            if screenshot:
                screenshot_bytes = await page.screenshot(full_page=False, type="png")
                result.screenshot = base64.b64encode(screenshot_bytes).decode("utf-8")

            # Extract metadata
            result.metadata = await page.evaluate("""
                () => {
                    return {
                        meta_description: document.querySelector('meta[name="description"]')?.content || null,
                        meta_keywords: document.querySelector('meta[name="keywords"]')?.content || null,
                        canonical: document.querySelector('link[rel="canonical"]')?.href || null,
                        og_title: document.querySelector('meta[property="og:title"]')?.content || null,
                        og_description: document.querySelector('meta[property="og:description"]')?.content || null,
                        og_image: document.querySelector('meta[property="og:image"]')?.content || null,
                        h1: document.querySelector('h1')?.innerText || null,
                        h2_count: document.querySelectorAll('h2').length,
                        link_count: document.querySelectorAll('a').length,
                    }
                }
            """)

            result.success = result.status_code == 200

        except Exception as e:
            result.error = str(e)
            result.success = False

        finally:
            await page.close()

        return result

    async def extract_forms(self, url: str) -> list[dict]:
        """Extract form information from a page."""
        if not self._initialized:
            await self.initialize()

        page = await self.context.new_page()
        forms = []

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            forms_data = await page.evaluate("""
                () => {
                    const forms = [];
                    document.querySelectorAll('form').forEach((form, index) => {
                        const inputs = [];
                        form.querySelectorAll('input, select, textarea').forEach(input => {
                            inputs.push({
                                type: input.type || input.tagName.toLowerCase(),
                                name: input.name || input.id || null,
                                id: input.id || null,
                                required: input.required || false,
                                placeholder: input.placeholder || null,
                            });
                        });

                        forms.push({
                            index,
                            action: form.action || window.location.href,
                            method: form.method || 'GET',
                            input_count: inputs.length,
                            inputs: inputs.slice(0, 10),  // Limit to first 10 inputs
                        });
                    });
                    return forms;
                }
            """)
            forms = forms_data

        except Exception as e:
            print(f"Error extracting forms: {e}")

        finally:
            await page.close()

        return forms

    async def check_eligibility_page(
        self,
        url: str,
        keywords: list[str] = None,
    ) -> dict:
        """Check if a page contains eligibility-related content."""
        if keywords is None:
            keywords = [
                "student",
                "education",
                "startup",
                "free trial",
                "credits",
                "beta",
                "early access",
                "discount",
                "promotion",
            ]

        result = await self.verify_url(url, screenshot=False)

        if not result.success or not result.content:
            return {"eligible": False, "reason": "Could not access page content"}

        content_lower = result.content.lower()
        found_keywords = [kw for kw in keywords if kw.lower() in content_lower]

        return {
            "eligible": len(found_keywords) > 0,
            "found_keywords": found_keywords,
            "keyword_count": len(found_keywords),
            "content_length": len(result.content),
        }

    async def check_signup_flow(
        self,
        url: str,
        max_steps: int = 3,
    ) -> dict:
        """Attempt to navigate through a signup flow (read-only)."""
        if not self._initialized:
            await self.initialize()

        page = await self.context.new_page()
        flow_data = {
            "steps": [],
            "success": False,
            "signup_detected": False,
        }

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Check for signup indicators
            signup_indicators = await page.evaluate("""
                () => {
                    const text = document.body.innerText.toLowerCase();
                    return {
                        has_signup: text.includes('sign up') || text.includes('register') || text.includes('create account'),
                        has_login: text.includes('log in') || text.includes('sign in') || text.includes('login'),
                        button_count: document.querySelectorAll('button').length,
                        input_count: document.querySelectorAll('input').length,
                    }
                }
            """)

            flow_data["signup_detected"] = signup_indicators["has_signup"]
            flow_data["steps"].append({
                "action": "page_load",
                "url": url,
                "indicators": signup_indicators,
            })

            # If signup detected, try to find and inspect the signup form
            if signup_indicators["has_signup"]:
                forms = await self.extract_forms(url)
                flow_data["steps"].append({
                    "action": "form_extraction",
                    "form_count": len(forms),
                    "forms": forms[:2],  # Limit to first 2 forms
                })

            flow_data["success"] = True

        except Exception as e:
            flow_data["error"] = str(e)
            flow_data["success"] = False

        finally:
            await page.close()

        return flow_data


# Global instance
_browser_service: Optional[BrowserAutomationService] = None


def get_browser_service() -> BrowserAutomationService:
    """Get or create the global browser service instance."""
    global _browser_service
    if _browser_service is None:
        _browser_service = BrowserAutomationService()
    return _browser_service
