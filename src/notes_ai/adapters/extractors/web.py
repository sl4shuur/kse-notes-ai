import asyncio
from concurrent.futures import ProcessPoolExecutor

import trafilatura
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from notes_ai.interfaces import TextExtractor
from notes_ai.loggers import CustomLogger
from notes_ai.models import ExtractedContent, Source, WebExtractionMetadata

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)


def _fetch_with_playwright_sync(url: str) -> str:
    """Fetch page content using Playwright in a separate process (sync wrapper)."""

    async def _fetch():
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--headless=new",
                ],
            )
            # context for "true user" behavior
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={
                    "Referer": "https://www.google.com/",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            # custom "stealth"
            await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60 * 1000)

                try:
                    # wait for main content selectors
                    await page.wait_for_selector(
                        "article, h1, section", state="attached", timeout=15 * 1000
                    )
                except PlaywrightTimeoutError:
                    # If not found, just go ahead
                    pass

                # Small wait for hydration/rendering if needed
                await page.wait_for_timeout(2000)
            except Exception as e:
                # Log warning but proceed to extract whatever content loaded
                print(f"Playwright navigation warning (proceeding anyway): {e}")

            content = await page.content()
            await browser.close()
            return content

    # Create new event loop for this process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_fetch())
    finally:
        loop.close()


class WebExtractor(TextExtractor):
    def __init__(self, logger: CustomLogger):
        self.logger = logger

    def supports(self, source: Source) -> bool:
        source_type = source.input_type.lower()
        return source_type == "web"

    async def extract(self, source: Source) -> ExtractedContent:
        """
        Extract article text from a web page using trafilatura with Playwright fallback.

        Args:
            url: URL of the article.
            logger: Custom logger instance.
            include_metadata: If True, includes title, date, author in output.

        Returns:
            str: Extracted article text (markdown format if include_metadata=True).
        """
        url = source.location
        logger = self.logger
        logger.debug(f"Extracting article from: {url}")

        try:
            # Try simple fetch first
            downloaded = trafilatura.fetch_url(url)

            # If None or too short, use Playwright for dynamic content
            if not downloaded or len(downloaded) < 500:
                logger.debug("Using Playwright for dynamic content")

                # Run Playwright in a separate process to avoid event loop issues
                loop = asyncio.get_running_loop()
                with ProcessPoolExecutor(max_workers=1) as executor:
                    downloaded = await loop.run_in_executor(
                        executor, _fetch_with_playwright_sync, url
                    )

            text = trafilatura.extract(
                downloaded, include_comments=False, include_tables=True, output_format="markdown"
            )
            extracted_metadata = trafilatura.extract_metadata(downloaded)

            if not text:
                raise ValueError(f"No content extracted from: {url}")

            logger.debug(f"Extracted article: {len(text)} chars")
            return ExtractedContent(
                text=text,
                metadata=WebExtractionMetadata(
                    title=getattr(extracted_metadata, "title", None),
                    author=getattr(extracted_metadata, "author", None),
                    published_date=getattr(extracted_metadata, "date", None),
                    url=getattr(extracted_metadata, "url", None) or url,
                ),
            )
        except PlaywrightTimeoutError:
            logger.error(f"Playwright timeout while fetching: {url}")
            raise
        except Exception as e:
            logger.error(f"Error extracting article from {url}: {e}")
            raise
