"""
CompanyCam public share link scraper.
Uses Playwright to open a CompanyCam shared project link,
extract all photo URLs, and download them to a local folder.
"""

import re
import time
import shutil
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import TEMP_PHOTOS_DIR


def scrape_project(share_url: str, clear_temp: bool = True) -> tuple[list[Path], dict]:
    """
    Open a CompanyCam public share link, download all photos.

    Returns:
        (photo_paths, project_info)
        photo_paths: list of local Paths to downloaded images
        project_info: dict with 'name', 'address', 'photo_count'
    """
    if clear_temp and TEMP_PHOTOS_DIR.exists():
        shutil.rmtree(TEMP_PHOTOS_DIR)
    TEMP_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    photo_urls = []
    project_info = {"name": "", "address": "", "photo_count": 0}

    print(f"Opening CompanyCam share link...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        # Intercept image requests to capture full-res URLs
        intercepted_urls: set[str] = set()

        def handle_response(response):
            url = response.url
            if _is_photo_url(url) and url not in intercepted_urls:
                intercepted_urls.add(url)

        page.on("response", handle_response)

        try:
            page.goto(share_url, wait_until="networkidle", timeout=30000)
        except PlaywrightTimeout:
            print("Page load timed out — continuing with what loaded.")

        # Try to grab project name / address from page title or headings
        try:
            title = page.title()
            project_info["name"] = title.replace("CompanyCam", "").strip(" |-")
        except Exception:
            pass

        try:
            heading = page.locator("h1").first.inner_text(timeout=3000)
            if heading:
                project_info["name"] = heading.strip()
        except Exception:
            pass

        # Scroll to load all lazy-loaded photos
        print("Scrolling to load all photos...")
        _scroll_to_bottom(page)

        # Collect all <img> src attributes that look like photo URLs
        img_srcs = page.eval_on_selector_all(
            "img",
            "els => els.map(el => el.src || el.getAttribute('data-src') || '').filter(Boolean)"
        )
        for src in img_srcs:
            if _is_photo_url(src):
                intercepted_urls.add(src)

        # Also try srcset
        srcsets = page.eval_on_selector_all(
            "img[srcset]",
            "els => els.map(el => el.srcset)"
        )
        for srcset in srcsets:
            for part in srcset.split(","):
                url = part.strip().split(" ")[0]
                if _is_photo_url(url):
                    intercepted_urls.add(url)

        photo_urls = _deduplicate_photos(list(intercepted_urls))
        print(f"Found {len(photo_urls)} photos.")

        browser.close()

    # Download all photos
    photo_paths = _download_photos(photo_urls)
    project_info["photo_count"] = len(photo_paths)

    return photo_paths, project_info


def _is_photo_url(url: str) -> bool:
    """Return True if URL looks like a CompanyCam photo (not a thumbnail icon)."""
    if not url:
        return False
    lower = url.lower()
    # Must be an image format
    if not any(ext in lower for ext in [".jpg", ".jpeg", ".png", ".webp"]):
        return False
    # Exclude tiny icons / UI assets
    skip_patterns = ["favicon", "logo", "icon", "avatar", "thumb16", "thumb32", "sprite"]
    if any(p in lower for p in skip_patterns):
        return False
    # Prefer CompanyCam CDN or companycam domains
    if "companycam" in lower or "imagedelivery" in lower or "cloudfront" in lower:
        return True
    # Accept any other image URL found on the page
    return True


def _deduplicate_photos(urls: list[str]) -> list[str]:
    """
    Remove duplicates and prefer highest-resolution version of each image.
    CompanyCam often serves the same image at multiple sizes via query params.
    """
    # Group by base URL (strip query string size params)
    base_map: dict[str, str] = {}
    for url in urls:
        base = re.split(r"\?", url)[0]
        # Keep the URL with the longest query string (usually highest-res)
        existing = base_map.get(base, "")
        if len(url) >= len(existing):
            base_map[base] = url
    return list(base_map.values())


def _scroll_to_bottom(page, pause: float = 1.5, max_scrolls: int = 30):
    """Scroll the page incrementally to trigger lazy-load of all photos."""
    last_height = 0
    for _ in range(max_scrolls):
        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        time.sleep(pause)
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def _download_photos(urls: list[str]) -> list[Path]:
    """Download photos to TEMP_PHOTOS_DIR. Returns list of saved Paths."""
    paths = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    })

    for i, url in enumerate(urls, start=1):
        ext = _get_extension(url)
        dest = TEMP_PHOTOS_DIR / f"photo_{i:03d}{ext}"
        try:
            resp = session.get(url, timeout=20, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            paths.append(dest)
            print(f"  Downloaded {i}/{len(urls)}: {dest.name}")
        except Exception as e:
            print(f"  Warning: could not download photo {i}: {e}")

    return paths


def _get_extension(url: str) -> str:
    path = url.split("?")[0].lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        if path.endswith(ext):
            return ext if ext != ".jpeg" else ".jpg"
    return ".jpg"
