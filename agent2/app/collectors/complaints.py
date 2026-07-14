"""
app/collectors/complaints.py

Scrapes public complaint/review websites for fraud-related posts.
Uses Selenium with headless Chrome.
Paginates through each configured site and extracts title, body, date, and URL.
Stores results via StorageService — never writes to MongoDB directly.
"""

import time
import hashlib
from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

from app.config.constants import COMPLAINT_SITES, POLL_INTERVAL_SECONDS
from app.models.raw_post import RawPost
from app.normalizers.complaints import ComplaintsNormalizer
from app.services.storage import StorageService

# Seconds to wait for page elements to appear
PAGE_LOAD_TIMEOUT = 15

# Seconds to pause between page navigations (be a good citizen)
PAGE_DELAY = 2

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# ---------------------------------------------------------------------------
# Per-site scraping configurations
# Each entry defines how to locate posts on a given site's structure.
# ---------------------------------------------------------------------------

SITE_SELECTORS: dict[str, dict] = {
    "complaintsboard": {
        "post_container": "div.complaint-item, article.complaint, div.post",
        "title":          "h2 a, h3 a, .complaint-title a",
        "body":           "p.complaint-text, div.complaint-body, .post-content p",
        "date":           "time, .date, span.post-date",
        "link":           "h2 a, h3 a, .complaint-title a",
    },
    "mouthshut": {
        "post_container": "div.review-block, div.review-wrap, .review-item",
        "title":          "h2.review-title, .review-heading, strong.title",
        "body":           "div.review-description, p.review-body, .review-text",
        "date":           "span.date, time, .review-date",
        "link":           "a.review-link, h2 a",
    },
    # Generic fallback used when a site name doesn't match any key above.
    "_generic": {
        "post_container": "article, div.post, div.complaint, div.review",
        "title":          "h1, h2, h3",
        "body":           "p, div.content, div.body",
        "date":           "time, .date, span.date",
        "link":           "a",
    },
}


class ComplaintsCollector:
    """
    Scrapes complaint and review websites for fraud-related posts.

    Configured entirely through COMPLAINT_SITES in constants.py.
    No hardcoded URLs in this file.

    Usage:
        collector = ComplaintsCollector()
        collector.collect_once()   # one sweep across all sites
        collector.run()            # continuous polling loop
    """

    def __init__(self) -> None:
        self.normalizer = ComplaintsNormalizer()
        self.storage = StorageService()

    # -----------------------------------------------------------------------
    # Public: single sweep
    # -----------------------------------------------------------------------

    def collect_once(self) -> int:
        """
        Scrape all configured complaint sites for one sweep.
        Returns total number of newly inserted posts.
        """
        logger.info(
            "ComplaintsCollector.collect_once: scraping {} site(s).",
            len(COMPLAINT_SITES),
        )

        driver = self._build_driver()
        total_inserted = 0

        try:
            for site_config in COMPLAINT_SITES:
                name  = site_config["name"]
                url   = site_config["url"]
                pages = site_config.get("pages", 1)

                try:
                    posts = self._scrape_site(driver, name, url, pages)
                    if not posts:
                        logger.warning("ComplaintsCollector: no posts from '{}'.", name)
                        continue

                    result = self.storage.store(posts)
                    total_inserted += result["inserted"]
                    logger.info(
                        "'{}': stored={}, duplicates={}, failed={}.",
                        name,
                        result["inserted"],
                        result["duplicates"],
                        result["failed"],
                    )

                except WebDriverException as e:
                    logger.error("ComplaintsCollector: WebDriver error on '{}' — {}", name, e)

                except Exception as e:
                    logger.error("ComplaintsCollector: unexpected error on '{}' — {}", name, e)

        finally:
            driver.quit()
            logger.debug("ComplaintsCollector: browser closed.")

        logger.info("ComplaintsCollector.collect_once complete. Total stored: {}.", total_inserted)
        return total_inserted

    # -----------------------------------------------------------------------
    # Public: continuous loop
    # -----------------------------------------------------------------------

    def run(self) -> None:
        """Poll all configured complaint sites continuously."""
        logger.info(
            "ComplaintsCollector.run: starting loop (interval={}s).",
            POLL_INTERVAL_SECONDS,
        )
        while True:
            try:
                self.collect_once()
            except Exception as e:
                logger.error("ComplaintsCollector.run: unexpected error — {}", e)

            logger.debug("ComplaintsCollector: sleeping {}s.", POLL_INTERVAL_SECONDS)
            time.sleep(POLL_INTERVAL_SECONDS)

    # -----------------------------------------------------------------------
    # Scraping
    # -----------------------------------------------------------------------

    def _scrape_site(
        self,
        driver: webdriver.Chrome,
        site_name: str,
        url_template: str,
        pages: int,
    ) -> list[RawPost]:
        """Paginate through a site and extract posts from each page."""
        selectors = SITE_SELECTORS.get(site_name, SITE_SELECTORS["_generic"])
        all_posts: list[RawPost] = []

        for page_num in range(1, pages + 1):
            url = url_template.format(page=page_num)
            logger.debug("ComplaintsCollector: loading page {} — {}", page_num, url)

            try:
                driver.get(url)
                self._wait_for_page(driver, selectors["post_container"])
                self._scroll_to_bottom(driver)

                containers = driver.find_elements(
                    By.CSS_SELECTOR, selectors["post_container"]
                )

                if not containers:
                    logger.warning(
                        "ComplaintsCollector: no containers found on {} page {}.",
                        site_name, page_num,
                    )
                    break

                for container in containers:
                    post = self._extract_post(container, selectors, site_name, url)
                    if post:
                        all_posts.append(post)

                logger.debug(
                    "ComplaintsCollector: page {} — {} posts extracted.",
                    page_num, len(all_posts),
                )
                time.sleep(PAGE_DELAY)

            except TimeoutException:
                logger.warning(
                    "ComplaintsCollector: timeout on {} page {} — skipping.", site_name, page_num
                )
                break

        return all_posts

    def _extract_post(
        self,
        container,
        selectors: dict,
        site_name: str,
        page_url: str,
    ) -> Optional[RawPost]:
        """Extract a single RawPost from a page container element."""
        try:
            title = self._get_text(container, selectors["title"])
            body  = self._get_text(container, selectors["body"])
            text  = body or title

            if not text:
                return None

            link       = self._get_href(container, selectors["link"]) or page_url
            date_str   = self._get_text(container, selectors["date"])

            raw_data = {
                "title": title,
                "text": text,
                "url": link,
                "date": date_str,
                "author": "",
                "site_name": site_name,
                "page_url": page_url,
            }
            return self.normalizer.normalize(raw_data)

        except Exception as e:
            logger.warning("ComplaintsCollector: failed to extract post — {}", e)
            return None

    # -----------------------------------------------------------------------
    # DOM helpers
    # -----------------------------------------------------------------------

    def _get_text(self, container, css_selector: str) -> str:
        """Return the stripped text of the first matching element, or ''."""
        try:
            el = container.find_element(By.CSS_SELECTOR, css_selector)
            return el.text.strip()
        except NoSuchElementException:
            return ""

    def _get_href(self, container, css_selector: str) -> Optional[str]:
        """Return the href of the first matching element, or None."""
        try:
            el = container.find_element(By.CSS_SELECTOR, css_selector)
            return el.get_attribute("href") or None
        except NoSuchElementException:
            return None

    def _wait_for_page(self, driver: webdriver.Chrome, css_selector: str) -> None:
        """Wait until the main container selector is present in the DOM."""
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )

    def _scroll_to_bottom(self, driver: webdriver.Chrome) -> None:
        """Scroll to the bottom of the page to trigger lazy-loaded content."""
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.8)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _parse_date(self, date_str: str) -> datetime:
        """
        Try common date formats. Falls back to utcnow() if nothing matches.
        Add more formats to _DATE_FORMATS as needed.
        """
        _DATE_FORMATS = [
            "%B %d, %Y",        # January 5, 2024
            "%d %B %Y",         # 5 January 2024
            "%Y-%m-%d",         # 2024-01-05
            "%d/%m/%Y",         # 05/01/2024
            "%m/%d/%Y",         # 01/05/2024
            "%d-%m-%Y",         # 05-01-2024
            "%b %d, %Y",        # Jan 5, 2024
        ]
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
            except (ValueError, AttributeError):
                continue

        return datetime.now(tz=timezone.utc)

    # -----------------------------------------------------------------------
    # Browser
    # -----------------------------------------------------------------------

    def _build_driver(self) -> webdriver.Chrome:
        """Return a headless Chrome WebDriver instance."""
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"--user-agent={_USER_AGENT}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT + 5)
        logger.debug("ComplaintsCollector: headless Chrome started.")
        return driver
