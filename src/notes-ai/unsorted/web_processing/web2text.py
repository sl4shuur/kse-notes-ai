import requests
from curl_cffi import requests as curl_requests
import trafilatura
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from src.utils.logging_config import CustomLogger
import asyncio
from concurrent.futures import ProcessPoolExecutor


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

# deprecated: use extract_article_text instead
async def extract_article_text(url: str, logger: CustomLogger, include_metadata: bool = False) -> str:
    """
    Extract article text from a web page using trafilatura with Playwright fallback.

    Args:
        url: URL of the article.
        logger: Custom logger instance.
        include_metadata: If True, includes title, date, author in output.

    Returns:
        str: Extracted article text (markdown format if include_metadata=True).
    """
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
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                output_format="markdown",
                with_metadata=True
            )
        else:
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                output_format="txt"
            )

        if not text:
            raise ValueError(f"No content extracted from: {url}")

        logger.debug(f"Extracted article: {len(text)} chars")
        return text
    except PlaywrightTimeoutError:
        logger.error(f"Playwright timeout while fetching: {url}")
        raise
    except Exception as e:
        logger.error(f"Error extracting article from {url}: {e}")
        raise


def fetch_article_text(url: str, logger: CustomLogger, include_metadata: bool = False) -> str:
    # 1. Use cffi requests to get the page
    response = curl_requests.get(
        url,
        impersonate="chrome120",  # this sets a realistic user-agent
        headers={
            "Referer": "https://google.com",
            "Accept-Language": "en-US,en;q=0.9"
        },
        timeout=15
    )

    if response.status_code != 200:
        logger.warning(f"Initial fetch failed for: {url} with status {response.status_code}\n\n{response.text}\n\n")
        # Try to use Jina AI service to fetch HTML
        jina_url = f"https://r.jina.ai/{url}"

        headers = {
            'X-Return-Format': 'html',
            'X-Retain-Images': 'none'
        }
        new_response = requests.get(jina_url, headers=headers, timeout=30)
        if new_response.status_code != 200:
            logger.error(f"Failed to fetch via Jina for: {url} with status {new_response.status_code}\n\n{new_response.text}\n\n")
            raise Exception(f"Failed to fetch page: {url}. {new_response.text}")

    # 2. Get the HTML content (raw)
    dirty_html = response.text

    # 3. Extract text using trafilatura
    if include_metadata:
        text = trafilatura.extract(
            dirty_html,
            include_comments=False,
            include_tables=True,
            output_format="markdown",
            with_metadata=True
        )
    else:
        text = trafilatura.extract(
            dirty_html,
            include_comments=False,
            include_tables=True,
            output_format="txt"
        )
    if not text:
        logger.error(f"Extraction returned no content for: {url}")
        return ""
    logger.debug(f"Extracted article: {len(text)} chars")
    return text
