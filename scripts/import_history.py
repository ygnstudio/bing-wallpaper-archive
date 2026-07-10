from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import NamedTuple, Optional, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]
TARGET_START_DATE = date(2023, 5, 1)
TARGET_END_DATE = date(2026, 1, 31)
SUPPORTED_SUFFIXES = {".jpg", ".jpeg"}

DATE_VALID = "valid"
DATE_UNKNOWN = "unknown_date"
DATE_INVALID = "invalid_date"

STATUS_IMPORTED = "imported"
STATUS_DUPLICATE_HASH = "skipped_duplicate_hash"
STATUS_EXISTING_TARGET = "skipped_existing_target"
STATUS_EXISTING_HASH = "skipped_existing_hash"
STATUS_INVALID_DATE = "skipped_invalid_date"
STATUS_UNKNOWN_DATE = "skipped_unknown_date"
STATUS_OUT_OF_RANGE = "skipped_out_of_range"
STATUS_INVALID_IMAGE = "skipped_invalid_image"

COMPACT_DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
SEPARATED_DATE_RE = re.compile(r"^(\d{4})([-_.])(\d{2})\2(\d{2})$")
FORBIDDEN_URL_TOKENS = ("UHD", "4K", "3840X2160")


class DateParseResult(NamedTuple):
    status: str
    value: Optional[date]


class ImportEntry(NamedTuple):
    date: str
    source: str
    target: str
    sha256: str
    status: str
    reason: str
    kept_target: str
    existing_path: str


class ImportResult(NamedTuple):
    summary: dict
    imported: Tuple[ImportEntry, ...]
    skipped_duplicate_hash: Tuple[ImportEntry, ...]
    skipped_existing_target: Tuple[ImportEntry, ...]
    skipped_existing_hash: Tuple[ImportEntry, ...]
    skipped_invalid_or_unknown_date: Tuple[ImportEntry, ...]
    skipped_out_of_range: Tuple[ImportEntry, ...]
    skipped_invalid_image: Tuple[ImportEntry, ...]
    report_path: Path


def find_image_files(source_dir):
    """Find visible historical .jpg and .jpeg files under source_dir."""
    source_path = Path(source_dir)
    images = []
    for image_path in source_path.rglob("*"):
        if not image_path.is_file():
            continue
        try:
            relative_parts = image_path.relative_to(source_path).parts
        except ValueError:
            relative_parts = image_path.parts
        if any(part.startswith(".") for part in relative_parts):
            continue
        if image_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        images.append(image_path)
    return sorted(images, key=lambda path: path.resolve().as_posix())


def parse_date_from_filename(image_path):
    """Parse a supported date format from a history image filename."""
    stem = Path(image_path).stem
    match = COMPACT_DATE_RE.fullmatch(stem)
    if match:
        return build_date_parse_result(match.group(1), match.group(2), match.group(3))

    match = SEPARATED_DATE_RE.fullmatch(stem)
    if match:
        return build_date_parse_result(match.group(1), match.group(3), match.group(4))

    return DateParseResult(DATE_UNKNOWN, None)


def build_date_parse_result(year, month, day):
    """Build a date parse result from numeric date parts."""
    try:
        parsed_date = date(int(year), int(month), int(day))
    except ValueError:
        return DateParseResult(DATE_INVALID, None)
    return DateParseResult(DATE_VALID, parsed_date)


def is_in_target_range(wallpaper_date):
    """Return whether a date is inside the v0.2 history import range."""
    return TARGET_START_DATE <= wallpaper_date <= TARGET_END_DATE


def build_target_path(wallpaper_date):
    """Return the repository-relative target path for an import candidate."""
    return (
        f"wallpapers/{wallpaper_date.year:04d}/{wallpaper_date.month:02d}/"
        f"{wallpaper_date.strftime('%Y%m%d')}.jpg"
    )


def calculate_sha256(path):
    """Calculate the SHA256 hash for a local file."""
    sha256 = hashlib.sha256()
    with Path(path).open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_probable_jpeg(path):
    """Return whether a source file is non-empty and begins with a JPEG header."""
    image_path = Path(path)
    if image_path.stat().st_size == 0:
        return False
    with image_path.open("rb") as file_handle:
        return file_handle.read(2) == b"\xff\xd8"


def load_hashes(path):
    """Load data/hash.json using the existing hash metadata structure."""
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
    """Save data/hash.json with an atomic temporary-file replace."""
    atomic_write_json(path, hashes, sort_keys=True)


def load_metadata(path):
    """Load data/metadata.json using the existing metadata structure."""
    metadata_path = Path(path)
    if not metadata_path.exists():
        return {}

    content = metadata_path.read_text(encoding="utf-8")
    if not content.strip():
        return {}

    try:
        metadata = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {metadata_path}: {exc}") from exc

    if not isinstance(metadata, dict):
        raise ValueError(f"Expected {metadata_path} to contain a JSON object.")
    return metadata


def save_metadata(path, metadata):
    """Save data/metadata.json with stable keys and atomic replace."""
    sorted_metadata = {key: metadata[key] for key in sorted(metadata)}
    atomic_write_json(path, sorted_metadata)


def atomic_write_json(path, data, sort_keys=False):
    """Write JSON to path.tmp first, then atomically replace path."""
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = json_path.with_name(f"{json_path.name}.tmp")
    try:
        tmp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=sort_keys) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(json_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def copy_image(source, target):
    """Copy a history image into the repository standard path."""
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target_path)


def import_history(source_dir, root_dir=ROOT_DIR):
    """Import historical wallpaper images into the repository archive."""
    source_path = Path(source_dir).expanduser()
    if not source_path.exists() or not source_path.is_dir():
        raise ValueError(f"Source directory does not exist or is not a directory: {source_path}")

    root_path = Path(root_dir)
    hash_path = root_path / "data" / "hash.json"
    metadata_path = root_path / "data" / "metadata.json"
    hashes = load_hashes(hash_path)
    metadata = load_metadata(metadata_path)

    imported = []
    skipped_duplicate_hash = []
    skipped_existing_target = []
    skipped_existing_hash = []
    skipped_invalid_or_unknown_date = []
    skipped_out_of_range = []
    skipped_invalid_image = []
    kept_by_hash = {}

    image_paths = sorted(find_image_files(source_path), key=source_sort_key)
    print(f"Scanning source directory: {source_path.resolve().as_posix()}")
    print(f"Found supported image files: {len(image_paths)}")

    for image_path in image_paths:
        parse_result = parse_date_from_filename(image_path)
        source_display = image_path.resolve().as_posix()

        if parse_result.status == DATE_UNKNOWN:
            skipped_invalid_or_unknown_date.append(
                build_entry(
                    source_display,
                    STATUS_UNKNOWN_DATE,
                    reason="unknown_date",
                )
            )
            continue
        if parse_result.status == DATE_INVALID:
            skipped_invalid_or_unknown_date.append(
                build_entry(
                    source_display,
                    STATUS_INVALID_DATE,
                    reason="invalid_date",
                )
            )
            continue

        wallpaper_date = parse_result.value
        target_path = build_target_path(wallpaper_date)
        target_abs_path = root_path / target_path
        date_key = wallpaper_date.isoformat()

        if not is_in_target_range(wallpaper_date):
            skipped_out_of_range.append(
                build_entry(
                    source_display,
                    STATUS_OUT_OF_RANGE,
                    date_key,
                    target_path,
                    reason="outside_target_range",
                )
            )
            continue

        if not is_probable_jpeg(image_path):
            skipped_invalid_image.append(
                build_entry(
                    source_display,
                    STATUS_INVALID_IMAGE,
                    date_key,
                    target_path,
                    reason="empty_or_non_jpeg",
                )
            )
            continue

        source_hash = calculate_sha256(image_path)

        if target_abs_path.exists():
            target_hash = calculate_sha256(target_abs_path)
            if target_hash not in hashes:
                hashes[target_hash] = build_hash_record(date_key, target_path)
            update_metadata_record(metadata, date_key, target_path)
            skipped_existing_target.append(
                build_entry(
                    source_display,
                    STATUS_EXISTING_TARGET,
                    date_key,
                    target_path,
                    target_hash,
                    reason="target_exists",
                )
            )
            if source_hash == target_hash:
                kept_by_hash.setdefault(source_hash, target_path)
            continue

        if source_hash in kept_by_hash:
            skipped_duplicate_hash.append(
                build_entry(
                    source_display,
                    STATUS_DUPLICATE_HASH,
                    date_key,
                    target_path,
                    source_hash,
                    reason="duplicate_hash",
                    kept_target=kept_by_hash[source_hash],
                )
            )
            continue

        if source_hash in hashes:
            skipped_existing_hash.append(
                build_entry(
                    source_display,
                    STATUS_EXISTING_HASH,
                    date_key,
                    target_path,
                    source_hash,
                    reason="hash_exists",
                    existing_path=get_existing_hash_path(hashes, source_hash),
                )
            )
            continue

        copy_image(image_path, target_abs_path)
        hashes[source_hash] = build_hash_record(date_key, target_path)
        update_metadata_record(metadata, date_key, target_path)
        kept_by_hash[source_hash] = target_path
        imported.append(
            build_entry(
                source_display,
                STATUS_IMPORTED,
                date_key,
                target_path,
                source_hash,
            )
        )

    save_hashes(hash_path, hashes)
    save_metadata(metadata_path, metadata)

    result = build_result(
        imported,
        skipped_duplicate_hash,
        skipped_existing_target,
        skipped_existing_hash,
        skipped_invalid_or_unknown_date,
        skipped_out_of_range,
        skipped_invalid_image,
        len(image_paths),
        root_path / "reports" / "history_import.md",
    )
    write_report(source_path, result, root_path)
    print_summary(result, root_path)
    return result


def source_sort_key(image_path):
    """Sort source images by date ascending, then source path ascending."""
    parse_result = parse_date_from_filename(image_path)
    date_key = parse_result.value or date.max
    return (date_key, image_path.resolve().as_posix())


def build_entry(
    source,
    status,
    date_key="",
    target_path="",
    sha256="",
    reason="",
    kept_target="",
    existing_path="",
):
    """Build one import report entry."""
    return ImportEntry(
        date=date_key,
        source=source,
        target=target_path,
        sha256=sha256,
        status=status,
        reason=reason,
        kept_target=kept_target,
        existing_path=existing_path,
    )


def build_hash_record(date_key, target_path):
    """Build the existing data/hash.json record shape for a history image."""
    return {
        "date": date_key,
        "path": target_path,
        "url": "",
    }


def update_metadata_record(metadata, date_key, target_path):
    """Insert or update a placeholder metadata record without clearing credits."""
    existing = metadata.get(date_key, {})
    if not isinstance(existing, dict):
        existing = {}

    metadata[date_key] = {
        "date": date_key,
        "title": keep_string(existing.get("title", "")),
        "copyright": keep_string(existing.get("copyright", "")),
        "url": keep_url(existing.get("url", "")),
        "image": target_path,
    }


def keep_string(value):
    """Keep a string field only when it is a string."""
    return value if isinstance(value, str) else ""


def keep_url(value):
    """Keep an existing URL unless it points at a forbidden high-resolution file."""
    if not isinstance(value, str):
        return ""
    upper_value = value.upper()
    if any(token in upper_value for token in FORBIDDEN_URL_TOKENS):
        return ""
    return value


def get_existing_hash_path(hashes, file_hash):
    """Return the existing repository path recorded for a known hash."""
    record = hashes.get(file_hash)
    if isinstance(record, dict) and isinstance(record.get("path"), str):
        return record["path"]
    return ""


def build_result(
    imported,
    skipped_duplicate_hash,
    skipped_existing_target,
    skipped_existing_hash,
    skipped_invalid_or_unknown_date,
    skipped_out_of_range,
    skipped_invalid_image,
    total_source_images,
    report_path,
):
    """Build a result object with stable summary counts."""
    skipped_invalid_date = sum(
        1 for entry in skipped_invalid_or_unknown_date if entry.status == STATUS_INVALID_DATE
    )
    skipped_unknown_date = sum(
        1 for entry in skipped_invalid_or_unknown_date if entry.status == STATUS_UNKNOWN_DATE
    )
    summary = {
        "total_source_images": total_source_images,
        "imported": len(imported),
        "skipped_duplicate_hash": len(skipped_duplicate_hash),
        "skipped_existing_target": len(skipped_existing_target),
        "skipped_existing_hash": len(skipped_existing_hash),
        "skipped_invalid_date": skipped_invalid_date,
        "skipped_unknown_date": skipped_unknown_date,
        "skipped_out_of_range": len(skipped_out_of_range),
        "skipped_invalid_image": len(skipped_invalid_image),
    }
    return ImportResult(
        summary=summary,
        imported=tuple(sorted(imported, key=entry_sort_key)),
        skipped_duplicate_hash=tuple(sorted(skipped_duplicate_hash, key=entry_sort_key)),
        skipped_existing_target=tuple(sorted(skipped_existing_target, key=entry_sort_key)),
        skipped_existing_hash=tuple(sorted(skipped_existing_hash, key=entry_sort_key)),
        skipped_invalid_or_unknown_date=tuple(
            sorted(skipped_invalid_or_unknown_date, key=lambda entry: entry.source)
        ),
        skipped_out_of_range=tuple(sorted(skipped_out_of_range, key=entry_sort_key)),
        skipped_invalid_image=tuple(sorted(skipped_invalid_image, key=entry_sort_key)),
        report_path=report_path,
    )


def entry_sort_key(entry):
    """Sort report entries by date, then source path."""
    return (entry.date or "9999-99-99", entry.source)


def write_report(source_dir, result, root_dir=ROOT_DIR):
    """Write reports/history_import.md with stable Markdown sections."""
    report_path = result.report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(source_dir, result), encoding="utf-8")
    return report_path


def build_report(source_dir, result):
    """Build the Markdown import report."""
    lines = [
        "# History Import Report",
        "",
        "## Source Directory",
        "",
        f"- Path: {Path(source_dir).resolve().as_posix()}",
        "",
        "## Target Range",
        "",
        f"- Start: {TARGET_START_DATE.isoformat()}",
        f"- End: {TARGET_END_DATE.isoformat()}",
        "",
        "## Summary",
        "",
        f"- Total source images: {result.summary['total_source_images']}",
        f"- Imported: {result.summary['imported']}",
        f"- Skipped duplicate hash: {result.summary['skipped_duplicate_hash']}",
        f"- Skipped existing target: {result.summary['skipped_existing_target']}",
        f"- Skipped existing hash: {result.summary['skipped_existing_hash']}",
        f"- Skipped invalid date: {result.summary['skipped_invalid_date']}",
        f"- Skipped unknown date: {result.summary['skipped_unknown_date']}",
        f"- Skipped out of range: {result.summary['skipped_out_of_range']}",
        f"- Skipped invalid image: {result.summary['skipped_invalid_image']}",
        "",
        "## Imported Files",
        "",
        markdown_table(
            ["Date", "Source", "Target"],
            [[entry.date, entry.source, entry.target] for entry in result.imported],
        ),
        "",
        "## Skipped Duplicate Hash",
        "",
        markdown_table(
            ["Date", "Source", "Kept Target", "SHA256"],
            [
                [entry.date, entry.source, entry.kept_target, entry.sha256]
                for entry in result.skipped_duplicate_hash
            ],
        ),
        "",
        "## Skipped Existing Target",
        "",
        markdown_table(
            ["Date", "Source", "Target"],
            [[entry.date, entry.source, entry.target] for entry in result.skipped_existing_target],
        ),
        "",
        "## Skipped Existing Hash",
        "",
        markdown_table(
            ["Date", "Source", "Existing Path", "SHA256"],
            [
                [entry.date, entry.source, entry.existing_path, entry.sha256]
                for entry in result.skipped_existing_hash
            ],
        ),
        "",
        "## Skipped Invalid or Unknown Date",
        "",
        markdown_table(
            ["Source", "Reason"],
            [[entry.source, entry.reason] for entry in result.skipped_invalid_or_unknown_date],
        ),
        "",
        "## Skipped Out of Range",
        "",
        markdown_table(
            ["Date", "Source", "Reason"],
            [[entry.date, entry.source, entry.reason] for entry in result.skipped_out_of_range],
        ),
        "",
        "## Skipped Invalid Image",
        "",
        markdown_table(
            ["Date", "Source", "Reason"],
            [[entry.date, entry.source, entry.reason] for entry in result.skipped_invalid_image],
        ),
        "",
        "## Notes",
        "",
        "- The source history directory was not modified.",
        "- Images were copied into repository-relative wallpapers/YYYY/MM/YYYYMMDD.jpg paths.",
        "- JSON files were written through temporary files before replacing the final files.",
        "",
    ]
    return "\n".join(lines)


def markdown_table(headers, rows):
    """Build a Markdown table, or a no-records marker for empty rows."""
    if not rows:
        return "No records."

    output = [
        "| " + " | ".join(escape_markdown_cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(escape_markdown_cell(value) for value in row) + " |")
    return "\n".join(output)


def escape_markdown_cell(value):
    """Escape Markdown table separators while keeping paths readable."""
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def print_summary(result, root_dir=ROOT_DIR):
    """Print concise import results for command-line runs."""
    print(f"Imported: {result.summary['imported']}")
    print(f"Skipped duplicate hash: {result.summary['skipped_duplicate_hash']}")
    print(f"Skipped existing target: {result.summary['skipped_existing_target']}")
    print(f"Skipped existing hash: {result.summary['skipped_existing_hash']}")
    print(f"Skipped invalid date: {result.summary['skipped_invalid_date']}")
    print(f"Skipped unknown date: {result.summary['skipped_unknown_date']}")
    print(f"Skipped out of range: {result.summary['skipped_out_of_range']}")
    print(f"Skipped invalid image: {result.summary['skipped_invalid_image']}")
    print(f"Wrote report: {relative_path(result.report_path, root_dir)}")


def relative_path(path, root_dir=ROOT_DIR):
    """Return a POSIX path relative to the repository root."""
    return Path(path).relative_to(Path(root_dir)).as_posix()


def parse_args(argv=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Import historical Bing wallpaper files into this archive."
    )
    parser.add_argument("source_dir", help="Directory containing historical wallpaper images.")
    return parser.parse_args(argv)


def main(argv=None):
    """Entry point for the history import script."""
    args = parse_args(argv)
    try:
        import_history(args.source_dir)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
