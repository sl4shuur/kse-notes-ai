from notes_ai.utils.loggers import CustomLogger
import asyncio
import trafilatura
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from concurrent.futures import ProcessPoolExecutor
import logging
from notes_ai.models import Source, ExtractedContent



def _fetch_with_playwright_sync(url: str) -> str:
        """Fetch page content using Playwright in a separate process (sync wrapper)."""

        async def _fetch():
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled",
                        "--no-sandbox", "--headless=new"]
                )
                # context for "true user" behavior
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    extra_http_headers={
                        'Referer': 'https://www.google.com/',
                        'Accept-Language': 'en-US,en;q=0.9',
                    }
                )
                # custom "stealth"
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                page = await context.new_page()

                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=60 * 1000)

                    try:
                        # wait for main content selectors
                        await page.wait_for_selector('article, h1, section', state='attached', timeout=15 * 1000)
                    except:
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



class WebExtractor:



    def __init__(self):
        self.logger = CustomLogger("WebExtractor")



    def supports(self, source: Source) -> bool:
        source_type = source.input_type.lower()
        return source_type in ["web", "website", "url"]



    async def extract(self, source: Source, include_metadata: bool = True, ) -> ExtractedContent:
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
                        executor,
                        _fetch_with_playwright_sync,
                        url
                    )

            # Extract with or without metadata
            if include_metadata:
                metadata = trafilatura.extract(
                    downloaded,
                    output_format="json",
                    with_metadata=True
                )

                
                text = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=True,
                    output_format="markdown"
                )           
            else:
                text = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=True,
                    output_format="markdown"
                )
                metadata = {}

            if not text:
                raise ValueError(f"No content extracted from: {url}")

            logger.debug(f"Extracted article: {len(text)} chars")
            return ExtractedContent(text=text, metadata= metadata)
        except PlaywrightTimeoutError:
            logger.error(f"Playwright timeout while fetching: {url}")
            raise
        except Exception as e:
            logger.error(f"Error extracting article from {url}: {e}")
            raise
