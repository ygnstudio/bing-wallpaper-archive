from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import NamedTuple

from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
WALLPAPER_DATE_RE = re.compile(r"^\d{8}\.jpg$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
INDEX_REQUIRED_FIELDS = {"date", "title", "copyright", "image", "thumbnail"}


class Issue(NamedTuple):
    type: str
    path: str
    message: str


class ArchiveCheckResult(NamedTuple):
    summary: dict
    errors: tuple[Issue, ...]
    warnings: tuple[Issue, ...]
    duplicate_hashes: tuple[tuple[str, tuple[str, ...]], ...]
    missing_thumbnails: tuple[tuple[str, str], ...]
    report_path: Path


def load_json(path, expected_type, errors, label=None):
    """Load a JSON file and record validation errors instead of mutating data."""
    json_path = Path(path)
    display_path = label or json_path.as_posix()
    if not json_path.exists():
        errors.append(Issue("json_missing", display_path, "JSON file does not exist."))
        return None

    try:
        content = json_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        errors.append(Issue("json_invalid", display_path, f"Invalid JSON: {exc}"))
        return None
    except OSError as exc:
        errors.append(Issue("json_unreadable", display_path, f"Cannot read JSON file: {exc}"))
        return None

    if not isinstance(data, expected_type):
        expected_name = expected_type.__name__
        errors.append(Issue("json_type", display_path, f"Expected JSON {expected_name}."))
        return None
    return data


def find_wallpapers(root_dir=ROOT_DIR):
    """Find .jpg wallpaper files under wallpapers/."""
    wallpapers_dir = Path(root_dir) / "wallpapers"
    if not wallpapers_dir.exists():
        return []
    return sorted(
        path for path in wallpapers_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".jpg"
    )


def find_thumbnails(root_dir=ROOT_DIR):
    """Find .jpg thumbnail files under thumbnails/."""
    thumbnails_dir = Path(root_dir) / "thumbnails"
    if not thumbnails_dir.exists():
        return []
    return sorted(
        path for path in thumbnails_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".jpg"
    )


def parse_wallpaper_date(image_path, root_dir=ROOT_DIR):
    """Parse wallpapers/YYYY/MM/YYYYMMDD.jpg and return a real date."""
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
    if not WALLPAPER_DATE_RE.fullmatch(filename):
        return None

    try:
        parsed_date = date(int(filename[:4]), int(filename[4:6]), int(filename[6:8]))
    except ValueError:
        return None

    if year_dir != f"{parsed_date.year:04d}":
        return None
    if month_dir != f"{parsed_date.month:02d}":
        return None
    return parsed_date


def check_wallpaper_paths(wallpapers, root_dir=ROOT_DIR):
    """Check wallpaper path format and return path validation errors."""
    root_path = Path(root_dir)
    errors = []
    for image_path in wallpapers:
        if parse_wallpaper_date(image_path, root_path) is None:
            errors.append(
                Issue(
                    "wallpaper_path",
                    relative_path(image_path, root_path),
                    "Expected wallpapers/YYYY/MM/YYYYMMDD.jpg with a real matching date.",
                )
            )
    return errors


def check_thumbnail_coverage(wallpapers, thumbnails, root_dir=ROOT_DIR):
    """Check missing and extra thumbnails for wallpaper files."""
    root_path = Path(root_dir)
    errors = []
    warnings = []
    missing_thumbnails = []
    expected_thumbnail_paths = set()

    for wallpaper_path in wallpapers:
        try:
            wallpaper_relative = wallpaper_path.relative_to(root_path / "wallpapers")
        except ValueError:
            continue
        expected_thumbnail = root_path / "thumbnails" / wallpaper_relative
        expected_thumbnail_relative = relative_path(expected_thumbnail, root_path)
        expected_thumbnail_paths.add(expected_thumbnail_relative)
        if not expected_thumbnail.exists():
            wallpaper_relative_path = relative_path(wallpaper_path, root_path)
            errors.append(
                Issue(
                    "missing_thumbnail",
                    wallpaper_relative_path,
                    f"Expected thumbnail is missing: {expected_thumbnail_relative}",
                )
            )
            missing_thumbnails.append((wallpaper_relative_path, expected_thumbnail_relative))

    for thumbnail_path in thumbnails:
        thumbnail_relative = relative_path(thumbnail_path, root_path)
        if thumbnail_relative not in expected_thumbnail_paths:
            warnings.append(
                Issue(
                    "extra_thumbnail",
                    thumbnail_relative,
                    "Thumbnail does not have a matching wallpaper.",
                )
            )

    return errors, warnings, missing_thumbnails


def check_index_json(root_dir, wallpapers, thumbnails, errors):
    """Check data/index.json consistency with local archive files."""
    root_path = Path(root_dir)
    index_path = root_path / "data" / "index.json"
    records = load_json(index_path, list, errors, "data/index.json")
    if records is None:
        return 0

    wallpaper_paths = {relative_path(path, root_path) for path in wallpapers}
    indexed_images = []
    seen_dates = {}

    for index, record in enumerate(records):
        record_path = f"data/index.json[{index}]"
        if not isinstance(record, dict):
            errors.append(Issue("index_record", record_path, "Index record must be an object."))
            continue

        missing_fields = sorted(INDEX_REQUIRED_FIELDS - set(record))
        for field in missing_fields:
            errors.append(Issue("index_field", record_path, f"Missing field: {field}"))

        for field in sorted(INDEX_REQUIRED_FIELDS & set(record)):
            value = record[field]
            if not isinstance(value, str):
                errors.append(Issue("index_field", record_path, f"Field must be a string: {field}"))

        date_text = record.get("date")
        record_date = parse_iso_date(date_text)
        if not isinstance(date_text, str) or not date_text:
            errors.append(Issue("index_date", record_path, "date must be a non-empty string."))
        elif record_date is None:
            errors.append(Issue("index_date", record_path, "date must be a real ISO date."))
        elif date_text in seen_dates:
            errors.append(
                Issue(
                    "index_duplicate_date",
                    record_path,
                    f"Duplicate date also appears at {seen_dates[date_text]}.",
                )
            )
        else:
            seen_dates[date_text] = record_path

        image_path = record.get("image")
        thumbnail_path = record.get("thumbnail")
        if isinstance(image_path, str):
            if not is_relative_posix_path(image_path):
                errors.append(Issue("index_image", record_path, "image must be a relative POSIX path."))
            else:
                indexed_images.append(image_path)
                resolved_image = repo_path(root_path, image_path)
                if not resolved_image.exists():
                    errors.append(Issue("index_image", image_path, "Image path does not exist."))
                parsed_date = parse_wallpaper_date(resolved_image, root_path)
                if parsed_date is not None and record_date is not None and parsed_date != record_date:
                    errors.append(
                        Issue(
                            "index_date_mismatch",
                            image_path,
                            "Record date does not match the wallpaper path date.",
                        )
                    )

        if isinstance(thumbnail_path, str):
            if not is_relative_posix_path(thumbnail_path):
                errors.append(
                    Issue("index_thumbnail", record_path, "thumbnail must be a relative POSIX path.")
                )
            elif not repo_path(root_path, thumbnail_path).exists():
                errors.append(Issue("index_thumbnail", thumbnail_path, "Thumbnail path does not exist."))

    indexed_image_set = set(indexed_images)
    for wallpaper_path in sorted(wallpaper_paths - indexed_image_set):
        errors.append(
            Issue("index_missing_wallpaper", wallpaper_path, "Wallpaper is missing from data/index.json.")
        )

    if len(records) != len(wallpaper_paths):
        errors.append(
            Issue(
                "index_count",
                "data/index.json",
                f"Index records ({len(records)}) do not match wallpapers ({len(wallpaper_paths)}).",
            )
        )

    return len(records)


def check_hash_json(root_dir, wallpapers, computed_hashes, errors):
    """Check data/hash.json coverage and SHA256 consistency."""
    root_path = Path(root_dir)
    hash_path = root_path / "data" / "hash.json"
    hash_records = load_json(hash_path, dict, errors, "data/hash.json")
    if hash_records is None:
        return 0

    hash_paths = set()
    for sha256, record in hash_records.items():
        record_path = f"data/hash.json[{sha256}]"
        if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None:
            errors.append(Issue("hash_key", record_path, "Hash key must be a lowercase SHA256 value."))
        if not isinstance(record, dict):
            errors.append(Issue("hash_record", record_path, "Hash record must be an object."))
            continue

        image_path = record.get("path")
        if not isinstance(image_path, str) or not image_path:
            errors.append(Issue("hash_path", record_path, "path must be a non-empty string."))
            continue
        if not is_relative_posix_path(image_path):
            errors.append(Issue("hash_path", record_path, "path must be a relative POSIX path."))
            continue
        if not image_path.startswith("wallpapers/"):
            errors.append(Issue("hash_path", image_path, "path must point to wallpapers/."))

        resolved_image = repo_path(root_path, image_path)
        if not resolved_image.exists():
            errors.append(Issue("hash_path", image_path, "Hash path does not exist."))
            continue

        hash_paths.add(image_path)
        actual_hash = computed_hashes.get(image_path)
        if actual_hash is not None and actual_hash != sha256:
            errors.append(
                Issue("hash_mismatch", image_path, "Recorded SHA256 does not match file contents.")
            )

    for wallpaper_path in sorted(relative_path(path, root_path) for path in wallpapers):
        if wallpaper_path not in hash_paths:
            errors.append(Issue("hash_missing", wallpaper_path, "Wallpaper is missing from data/hash.json."))

    return len(hash_records)


def check_metadata_json(root_dir, wallpapers, errors):
    """Check data/metadata.json coverage and metadata image paths."""
    root_path = Path(root_dir)
    metadata_path = root_path / "data" / "metadata.json"
    metadata_records = load_json(metadata_path, dict, errors, "data/metadata.json")
    if metadata_records is None:
        return 0

    valid_wallpaper_dates = {}
    for wallpaper_path in wallpapers:
        wallpaper_date = parse_wallpaper_date(wallpaper_path, root_path)
        if wallpaper_date is not None:
            valid_wallpaper_dates[wallpaper_date.isoformat()] = relative_path(wallpaper_path, root_path)

    for date_key, record in metadata_records.items():
        record_path = f"data/metadata.json[{date_key}]"
        parsed_date = parse_iso_date(date_key)
        if not isinstance(date_key, str) or parsed_date is None:
            errors.append(Issue("metadata_date", record_path, "Metadata key must be a real ISO date."))
        if not isinstance(record, dict):
            errors.append(Issue("metadata_record", record_path, "Metadata record must be an object."))
            continue

        for text_field in ("title", "copyright"):
            if text_field in record and not isinstance(record[text_field], str):
                errors.append(
                    Issue("metadata_field", record_path, f"{text_field} must be a string when present.")
                )

        image_path = record.get("image")
        if not isinstance(image_path, str) or not image_path:
            errors.append(Issue("metadata_image", record_path, "image must be a non-empty string."))
            continue
        if not is_relative_posix_path(image_path):
            errors.append(Issue("metadata_image", record_path, "image must be a relative POSIX path."))
            continue
        resolved_image = repo_path(root_path, image_path)
        if not resolved_image.exists():
            errors.append(Issue("metadata_image", image_path, "Metadata image path does not exist."))
            continue

        image_date = parse_wallpaper_date(resolved_image, root_path)
        if image_date is not None and parsed_date is not None and image_date != parsed_date:
            errors.append(
                Issue("metadata_date_mismatch", image_path, "Metadata key does not match image path date.")
            )

    for date_key, wallpaper_path in sorted(valid_wallpaper_dates.items()):
        if date_key not in metadata_records:
            errors.append(
                Issue("metadata_missing", wallpaper_path, "Wallpaper is missing from data/metadata.json.")
            )

    return len(metadata_records)


def check_duplicate_hashes(computed_hashes, errors):
    """Record duplicate file hashes across wallpapers/."""
    by_hash = {}
    for image_path, sha256 in computed_hashes.items():
        by_hash.setdefault(sha256, []).append(image_path)

    duplicate_hashes = []
    for sha256, paths in sorted(by_hash.items()):
        if len(paths) <= 1:
            continue
        sorted_paths = tuple(sorted(paths))
        duplicate_hashes.append((sha256, sorted_paths))
        errors.append(
            Issue("duplicate_hash", ", ".join(sorted_paths), "Multiple wallpapers have the same SHA256.")
        )
    return duplicate_hashes


def check_zero_byte_files(image_paths, root_dir=ROOT_DIR):
    """Check for zero-byte image files."""
    root_path = Path(root_dir)
    errors = []
    for image_path in image_paths:
        try:
            if image_path.stat().st_size == 0:
                errors.append(Issue("zero_byte", relative_path(image_path, root_path), "Image file is empty."))
        except OSError as exc:
            errors.append(Issue("stat_error", relative_path(image_path, root_path), f"Cannot stat file: {exc}"))
    return errors


def check_image_readability(image_paths, root_dir=ROOT_DIR):
    """Check whether images can be opened and verified by Pillow."""
    root_path = Path(root_dir)
    errors = []
    for image_path in image_paths:
        try:
            if image_path.stat().st_size == 0:
                continue
            with Image.open(image_path) as image:
                image.verify()
        except Exception as exc:
            errors.append(
                Issue(
                    "image_unreadable",
                    relative_path(image_path, root_path),
                    f"Pillow could not verify image: {exc}",
                )
            )
    return errors


def write_report(result, root_dir=ROOT_DIR):
    """Write reports/archive_check.md."""
    root_path = Path(root_dir)
    report_path = root_path / "reports" / "archive_check.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary = result.summary

    lines = [
        "# Archive Check Report",
        "",
        "## Summary",
        "",
        f"- Status: {summary['status']}",
        f"- Errors: {summary['errors']}",
        f"- Warnings: {summary['warnings']}",
        f"- Wallpapers: {summary['wallpapers']}",
        f"- Thumbnails: {summary['thumbnails']}",
        f"- Index Records: {summary['index_records']}",
        f"- Hash Records: {summary['hash_records']}",
        f"- Metadata Records: {summary['metadata_records']}",
        "",
        "## Errors",
        "",
        "| Type | Path | Message |",
        "|---|---|---|",
    ]
    lines.extend(issue_row(issue) for issue in result.errors)
    lines.extend(
        [
            "",
            "## Warnings",
            "",
            "| Type | Path | Message |",
            "|---|---|---|",
        ]
    )
    lines.extend(issue_row(issue) for issue in result.warnings)
    lines.extend(
        [
            "",
            "## Duplicate Hashes",
            "",
            "| SHA256 | Files |",
            "|---|---|",
        ]
    )
    for sha256, files in result.duplicate_hashes:
        lines.append(f"| {escape_markdown(sha256)} | {escape_markdown('<br>'.join(files))} |")

    lines.extend(
        [
            "",
            "## Missing Thumbnails",
            "",
            "| Wallpaper | Expected Thumbnail |",
            "|---|---|",
        ]
    )
    for wallpaper_path, thumbnail_path in result.missing_thumbnails:
        lines.append(f"| {escape_markdown(wallpaper_path)} | {escape_markdown(thumbnail_path)} |")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run_archive_check(root_dir=ROOT_DIR):
    """Run all archive integrity checks and write the report."""
    root_path = Path(root_dir)
    errors = []
    warnings = []

    wallpapers = find_wallpapers(root_path)
    thumbnails = find_thumbnails(root_path)
    errors.extend(check_wallpaper_paths(wallpapers, root_path))

    thumbnail_errors, thumbnail_warnings, missing_thumbnails = check_thumbnail_coverage(
        wallpapers, thumbnails, root_path
    )
    errors.extend(thumbnail_errors)
    warnings.extend(thumbnail_warnings)

    all_images = [*wallpapers, *thumbnails]
    errors.extend(check_zero_byte_files(all_images, root_path))
    errors.extend(check_image_readability(all_images, root_path))

    computed_hashes = calculate_wallpaper_hashes(wallpapers, root_path, errors)
    index_records = check_index_json(root_path, wallpapers, thumbnails, errors)
    hash_records = check_hash_json(root_path, wallpapers, computed_hashes, errors)
    metadata_records = check_metadata_json(root_path, wallpapers, errors)
    duplicate_hashes = check_duplicate_hashes(computed_hashes, errors)

    summary = {
        "status": "FAILED" if errors else "OK",
        "errors": len(errors),
        "warnings": len(warnings),
        "wallpapers": len(wallpapers),
        "thumbnails": len(thumbnails),
        "index_records": index_records,
        "hash_records": hash_records,
        "metadata_records": metadata_records,
    }
    provisional_result = ArchiveCheckResult(
        summary=summary,
        errors=tuple(errors),
        warnings=tuple(warnings),
        duplicate_hashes=tuple(duplicate_hashes),
        missing_thumbnails=tuple(missing_thumbnails),
        report_path=root_path / "reports" / "archive_check.md",
    )
    report_path = write_report(provisional_result, root_path)
    return ArchiveCheckResult(
        summary=summary,
        errors=tuple(errors),
        warnings=tuple(warnings),
        duplicate_hashes=tuple(duplicate_hashes),
        missing_thumbnails=tuple(missing_thumbnails),
        report_path=report_path,
    )


def calculate_wallpaper_hashes(wallpapers, root_dir, errors):
    """Calculate SHA256 hashes for wallpaper files."""
    root_path = Path(root_dir)
    computed_hashes = {}
    for wallpaper_path in wallpapers:
        wallpaper_relative = relative_path(wallpaper_path, root_path)
        try:
            computed_hashes[wallpaper_relative] = calculate_sha256(wallpaper_path)
        except OSError as exc:
            errors.append(Issue("hash_calculation", wallpaper_relative, f"Cannot hash file: {exc}"))
    return computed_hashes


def calculate_sha256(path):
    """Calculate SHA256 for a file."""
    sha256 = hashlib.sha256()
    with Path(path).open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def parse_iso_date(value):
    """Return a date for YYYY-MM-DD strings, otherwise None."""
    if not isinstance(value, str):
        return None
    try:
        parsed_date = date.fromisoformat(value)
    except ValueError:
        return None
    if value != parsed_date.isoformat():
        return None
    return parsed_date


def is_relative_posix_path(value):
    """Return whether value is a safe repository-relative POSIX path."""
    if not isinstance(value, str) or not value:
        return False
    if "\\" in value or value.startswith("/") or "\x00" in value:
        return False
    pure_path = PurePosixPath(value)
    if PureWindowsPath(value).drive:
        return False
    return bool(pure_path.parts) and ".." not in pure_path.parts


def repo_path(root_dir, relative_posix_path):
    """Resolve a repository-relative POSIX path under root_dir."""
    return Path(root_dir).joinpath(*PurePosixPath(relative_posix_path).parts)


def relative_path(path, root_dir=ROOT_DIR):
    """Return a POSIX path relative to root_dir when possible."""
    path = Path(path)
    root_path = Path(root_dir)
    try:
        return path.relative_to(root_path).as_posix()
    except ValueError:
        return path.as_posix()


def issue_row(issue):
    """Return a Markdown table row for one issue."""
    return (
        f"| {escape_markdown(issue.type)} | "
        f"{escape_markdown(issue.path)} | "
        f"{escape_markdown(issue.message)} |"
    )


def escape_markdown(value):
    """Escape minimal Markdown table separators."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def main(root_dir=ROOT_DIR):
    """Entry point for archive integrity checks."""
    result = run_archive_check(root_dir)
    print(f"Archive check status: {result.summary['status']}")
    print(f"Errors: {result.summary['errors']}")
    print(f"Warnings: {result.summary['warnings']}")
    print(f"Report: {relative_path(result.report_path, root_dir)}")
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
