from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BING_API_URL = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN"
BING_BASE_URL = "https://www.bing.com"
ROOT_DIR = Path(__file__).resolve().parents[1]
REQUEST_TIMEOUT = 30

STATUS_SAVED = "saved"
STATUS_EXISTS = "exists"
STATUS_BACKFILLED = "backfilled"
STATUS_DUPLICATE = "duplicate"


def fetch_bing_metadata():
    """Fetch metadata for today's Bing wallpaper."""
    print("Fetching Bing wallpaper metadata...")
    request = Request(
        BING_API_URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = response.read().decode("utf-8")

    data = json.loads(payload)
    images = data.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("Bing API response does not contain images[0].")
    if not isinstance(images[0], dict):
        raise ValueError("Bing API images[0] is not an object.")
    return images[0]


def build_image_url(metadata):
    """Build a normalized 1080P Bing image URL from image metadata."""
    raw_url = metadata.get("url")
    if not raw_url and metadata.get("urlbase"):
        raw_url = f"{metadata['urlbase']}_1920x1080.jpg"
    if not isinstance(raw_url, str) or not raw_url:
        raise ValueError("Bing image metadata does not contain a usable URL.")

    image_url = urljoin(BING_BASE_URL, raw_url)
    image_url = normalize_to_1080p(image_url)
    upper_url = image_url.upper()

    forbidden_tokens = ("UHD", "4K", "3840X2160")
    if any(token in upper_url for token in forbidden_tokens):
        raise ValueError(f"Refusing to download non-1080P image URL: {image_url}")
    if "1920x1080" not in image_url:
        raise ValueError(f"Image URL is not explicitly 1080P: {image_url}")

    return image_url


def normalize_to_1080p(image_url):
    """Normalize Bing resolution tokens to 1920x1080."""
    return re.sub(
        r"UHD|4K|\d{3,4}x\d{3,4}",
        "1920x1080",
        image_url,
        flags=re.IGNORECASE,
    )


def get_wallpaper_date(metadata, today=None):
    """Return the wallpaper date from metadata, falling back to local date."""
    startdate = metadata.get("startdate")
    if isinstance(startdate, str) and re.fullmatch(r"\d{8}", startdate):
        try:
            return datetime.strptime(startdate, "%Y%m%d").date()
        except ValueError:
            pass

    if today is not None:
        return today
    return date.today()


def get_wallpaper_path(wallpaper_date, root_dir=ROOT_DIR):
    """Return the archive path for a wallpaper date."""
    filename = wallpaper_date.strftime("%Y%m%d.jpg")
    return (
        Path(root_dir)
        / "wallpapers"
        / f"{wallpaper_date.year:04d}"
        / f"{wallpaper_date.month:02d}"
        / filename
    )


def get_hash_file(root_dir=ROOT_DIR):
    """Return the hash metadata file path."""
    return Path(root_dir) / "data" / "hash.json"


def load_hashes(path):
    """Load hash metadata from data/hash.json."""
    hash_path = Path(path)
    if not hash_path.exists():
        return {}

    content = hash_path.read_text(encoding="utf-8")
    if not content.strip():
        return {}

    try:
        hashes = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {hash_path}: {exc}") from exc

    if not isinstance(hashes, dict):
        raise ValueError(f"Expected {hash_path} to contain a JSON object.")
    return hashes


def save_hashes(path, hashes):
    """Save hash metadata to data/hash.json."""
    hash_path = Path(path)
    hash_path.parent.mkdir(parents=True, exist_ok=True)
    hash_path.write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def download_image(url):
    """Download image bytes from a 1080P URL."""
    print("Downloading 1080P image...")
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def calculate_sha256(content):
    """Calculate the SHA256 hash for image bytes."""
    return hashlib.sha256(content).hexdigest()


def process_wallpaper(metadata, root_dir=ROOT_DIR, downloader=download_image, today=None):
    """Download or deduplicate today's wallpaper based on metadata."""
    root_path = Path(root_dir)
    image_url = build_image_url(metadata)
    wallpaper_date = get_wallpaper_date(metadata, today=today)
    wallpaper_path = get_wallpaper_path(wallpaper_date, root_path)
    hash_file = get_hash_file(root_path)
    hashes = load_hashes(hash_file)

    if wallpaper_path.exists():
        existing_content = wallpaper_path.read_bytes()
        existing_hash = calculate_sha256(existing_content)
        if existing_hash in hashes:
            print(f"Target wallpaper already exists, skipping: {relative_path(wallpaper_path, root_path)}")
            return STATUS_EXISTS

        hashes[existing_hash] = build_hash_record(wallpaper_date, wallpaper_path, image_url, root_path)
        save_hashes(hash_file, hashes)
        print(
            "Target wallpaper already exists but hash record was missing; "
            f"backfilled hash: {relative_path(wallpaper_path, root_path)}"
        )
        print(f"Updated hash file: {relative_path(hash_file, root_path)}")
        return STATUS_BACKFILLED

    content = downloader(image_url)
    image_hash = calculate_sha256(content)
    if image_hash in hashes:
        print("Duplicate image hash found, skipping.")
        return STATUS_DUPLICATE

    wallpaper_path.parent.mkdir(parents=True, exist_ok=True)
    wallpaper_path.write_bytes(content)
    hashes[image_hash] = build_hash_record(wallpaper_date, wallpaper_path, image_url, root_path)
    save_hashes(hash_file, hashes)

    print(f"Saved wallpaper: {relative_path(wallpaper_path, root_path)}")
    print(f"Updated hash file: {relative_path(hash_file, root_path)}")
    return STATUS_SAVED


def build_hash_record(wallpaper_date, wallpaper_path, image_url, root_dir=ROOT_DIR):
    """Build a data/hash.json record for one image hash."""
    root_path = Path(root_dir)
    return {
        "date": wallpaper_date.isoformat(),
        "path": relative_path(wallpaper_path, root_path),
        "url": image_url,
    }


def relative_path(path, root_dir=ROOT_DIR):
    """Return a POSIX path relative to the repository root."""
    return Path(path).relative_to(Path(root_dir)).as_posix()


def main():
    """Entry point for downloading the daily Bing 1080P wallpaper."""
    try:
        metadata = fetch_bing_metadata()
        process_wallpaper(metadata)
    except HTTPError as exc:
        print(f"Error: HTTP request failed with status {exc.code}: {exc.reason}", file=sys.stderr)
        raise SystemExit(1) from exc
    except URLError as exc:
        print(f"Error: network request failed: {exc.reason}", file=sys.stderr)
        raise SystemExit(1) from exc
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
