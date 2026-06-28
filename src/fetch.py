#!/usr/bin/env python3
"""
Fetch HTML from native-stats.org/competition/WC/
Saves raw HTML to raw/wc_<timestamp>.html for parsing and debugging.
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from urllib import request, error, robotparser

# Config
SOURCE_URL = "https://native-stats.org/competition/WC/"
RAW_DIR = Path(__file__).parent.parent / "raw"
USER_AGENT = "Copa2026StaticBot/1.0 (+https://github.com/seu-usuario/copa2026-static)"
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def check_robots_txt() -> bool:
    """Check if we're allowed to fetch the URL per robots.txt."""
    rp = robotparser.RobotFileParser()
    rp.set_url("https://native-stats.org/robots.txt")
    try:
        rp.read()
        return rp.can_fetch(USER_AGENT, SOURCE_URL)
    except Exception as e:
        log.warning(f"Could not parse robots.txt: {e}, proceeding anyway")
        return True


def fetch_with_retry(url: str, retries: int = MAX_RETRIES) -> bytes:
    """Fetch URL with retry logic and exponential backoff."""
    req = request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(1, retries + 1):
        try:
            log.info(f"Fetching {url} (attempt {attempt}/{retries})")
            with request.urlopen(req, timeout=TIMEOUT) as resp:
                if resp.status != 200:
                    raise error.HTTPError(url, resp.status, f"HTTP {resp.status}", resp.headers, None)
                content = resp.read()
                log.info(f"Success: {len(content)} bytes")
                return content
        except error.HTTPError as e:
            if e.code == 429:  # Rate limited
                wait = RETRY_DELAY * (2 ** (attempt - 1))
                log.warning(f"Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
                continue
            elif e.code >= 500:
                wait = RETRY_DELAY * (2 ** (attempt - 1))
                log.warning(f"Server error {e.code}, waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                log.error(f"HTTP error {e.code}: {e.reason}")
                raise
        except error.URLError as e:
            wait = RETRY_DELAY * (2 ** (attempt - 1))
            log.warning(f"Network error: {e.reason}, waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            wait = RETRY_DELAY * (2 ** (attempt - 1))
            log.warning(f"Unexpected error: {e}, waiting {wait}s...")
            time.sleep(wait)

    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


def save_raw_html(content: bytes) -> Path:
    """Save raw HTML with timestamp filename."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = RAW_DIR / f"wc_{timestamp}.html"
    filepath.write_bytes(content)
    log.info(f"Saved raw HTML to {filepath}")
    return filepath


def main() -> int:
    log.info("Starting fetch from native-stats.org")

    # Check robots.txt
    if not check_robots_txt():
        log.error("robots.txt disallows fetching this URL")
        return 1

    # Fetch
    try:
        html = fetch_with_retry(SOURCE_URL)
    except Exception as e:
        log.error(f"Fetch failed: {e}")
        return 1

    # Save
    try:
        save_raw_html(html)
    except Exception as e:
        log.error(f"Save failed: {e}")
        return 1

    log.info("Fetch completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())