from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
INDEX_FILE = ROOT_DIR / "data" / "index.json"
METADATA_FILE = ROOT_DIR / "data" / "metadata.json"
DATE_FILENAME_RE = re.compile(r"^\d{8}\.jpg$")


def find_wallpaper_images(root_dir=ROOT_DIR):
    """Find valid wallpapers/YYYY/MM/YYYYMMDD.jpg files."""
    root_path = Path(root_dir)
    wallpapers_dir = root_path / "wallpapers"
    if not wallpapers_dir.exists():
        return []

    valid_images = []
    for image_path in sorted(wallpapers_dir.rglob("*.jpg")):
        if parse_date_from_filename(image_path, root_path) is None:
            print(f"Skipping invalid wallpaper path: {relative_path(image_path, root_path)}")
            continue
        valid_images.append(image_path)
    return valid_images


def parse_date_from_filename(image_path, root_dir=ROOT_DIR):
    """Parse and validate the date from wallpapers/YYYY/MM/YYYYMMDD.jpg."""
    root_path = Path(root_dir)
    image_path = Path(image_path)
    try:
        relative_image_path = image_path.relative_to(root_path / "wallpapers")
    except ValueError:
        return None

    parts = relative_image_path.parts
    if len(parts) != 3:
        return None

    year_dir, month_dir, filename = parts
    if not re.fullmatch(r"\d{4}", year_dir):
        return None
    if not re.fullmatch(r"\d{2}", month_dir):
        return None
    if not DATE_FILENAME_RE.fullmatch(filename):
        return None

    try:
        wallpaper_date = datetime.strptime(filename[:8], "%Y%m%d").date()
    except ValueError:
        return None

    if year_dir != f"{wallpaper_date.year:04d}":
        return None
    if month_dir != f"{wallpaper_date.month:02d}":
        return None

    return wallpaper_date


def get_thumbnail_path(image_path, root_dir=ROOT_DIR):
    """Map wallpapers/YYYY/MM/YYYYMMDD.jpg to thumbnails/YYYY/MM/YYYYMMDD.jpg."""
    root_path = Path(root_dir)
    relative_image_path = Path(image_path).relative_to(root_path / "wallpapers")
    return root_path / "thumbnails" / relative_image_path


def load_metadata(root_dir=ROOT_DIR):
    """Load data/metadata.json records if available."""
    root_path = Path(root_dir)
    metadata_path = root_path / "data" / "metadata.json"
    if not metadata_path.exists():
        print("Warning: data/metadata.json not found. Generating index with empty title and copyright.")
        return {}

    content = metadata_path.read_text(encoding="utf-8")
    if not content.strip():
        return {}

    try:
        metadata = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in data/metadata.json: {exc}") from exc

    if not isinstance(metadata, dict):
        raise ValueError("data/metadata.json must contain a JSON object.")

    print(f"Loaded metadata records: {len(metadata)}")
    return metadata


def build_index_record(image_path, root_dir=ROOT_DIR, metadata=None):
    """Build one data/index.json record for a valid wallpaper path."""
    root_path = Path(root_dir)
    wallpaper_date = parse_date_from_filename(image_path, root_path)
    if wallpaper_date is None:
        raise ValueError(f"Invalid wallpaper path: {relative_path(image_path, root_path)}")

    metadata_by_date = metadata or {}
    date_key = wallpaper_date.isoformat()
    metadata_record = metadata_by_date.get(date_key, {})
    title = metadata_record.get("title", "") if isinstance(metadata_record, dict) else ""
    copyright_text = (
        metadata_record.get("copyright", "") if isinstance(metadata_record, dict) else ""
    )

    thumbnail_path = get_thumbnail_path(image_path, root_path)
    return {
        "date": date_key,
        "title": title if isinstance(title, str) else "",
        "copyright": copyright_text if isinstance(copyright_text, str) else "",
        "image": relative_path(image_path, root_path),
        "thumbnail": relative_path(thumbnail_path, root_path),
    }


def build_index_records(root_dir=ROOT_DIR):
    """Build sorted index records for local wallpaper files."""
    root_path = Path(root_dir)
    metadata = load_metadata(root_path)
    records = []
    for image_path in find_wallpaper_images(root_path):
        thumbnail_path = get_thumbnail_path(image_path, root_path)
        if not thumbnail_path.exists():
            print(f"Warning: thumbnail not found for {relative_path(image_path, root_path)}")
        records.append(build_index_record(image_path, root_path, metadata))

    return sorted(records, key=lambda record: record["date"], reverse=True)


def write_index(records, root_dir=ROOT_DIR):
    """Write data/index.json with stable UTF-8 JSON formatting."""
    root_path = Path(root_dir)
    index_path = root_path / "data" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return index_path


def generate_index(root_dir=ROOT_DIR):
    """Generate data/index.json from local wallpaper and thumbnail files."""
    root_path = Path(root_dir)
    print("Scanning wallpapers directory...")
    records = build_index_records(root_path)
    if records:
        image_count = len(records)
        suffix = "image" if image_count == 1 else "images"
        print(f"Found {image_count} wallpaper {suffix}.")
        write_index(records, root_path)
        print("Wrote index file: data/index.json")
    else:
        print("No wallpaper images found.")
        write_index([], root_path)
        print("Wrote empty index file: data/index.json")
    return records


def relative_path(path, root_dir=ROOT_DIR):
    """Return a POSIX path relative to the repository root."""
    return Path(path).relative_to(Path(root_dir)).as_posix()


def main():
    """Entry point for generating data/index.json."""
    generate_index()


if __name__ == "__main__":
    main()
