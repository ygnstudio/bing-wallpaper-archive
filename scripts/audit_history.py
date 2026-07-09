from __future__ import annotations

import argparse
import hashlib
import json
import re
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

RANGE_IN = "in_range"
RANGE_BEFORE = "before_range"
RANGE_AFTER = "after_range"
RANGE_UNKNOWN = "unknown_date"
RANGE_INVALID = "invalid_date"

COMPACT_DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
SEPARATED_DATE_RE = re.compile(r"^(\d{4})([-_.])(\d{2})\2(\d{2})$")


class DateParseResult(NamedTuple):
    status: str
    value: Optional[date]


class AuditRecord(NamedTuple):
    source_path: Path
    source_display: str
    date_status: str
    parsed_date: Optional[date]
    range_status: str
    target_path: Optional[str]
    sha256: str
    has_existing_target_conflict: bool
    has_existing_hash_conflict: bool


class DuplicateGroup(NamedTuple):
    sha256: str
    records: Tuple[AuditRecord, ...]


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


def classify_range(parsed_date):
    """Classify a parsed date against the history import target range."""
    if parsed_date is None:
        return RANGE_UNKNOWN
    if parsed_date < TARGET_START_DATE:
        return RANGE_BEFORE
    if parsed_date > TARGET_END_DATE:
        return RANGE_AFTER
    return RANGE_IN


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


def load_existing_hashes(root_dir=ROOT_DIR):
    """Load existing data/hash.json keys for read-only conflict checks."""
    hash_path = Path(root_dir) / "data" / "hash.json"
    if not hash_path.exists():
        return set()

    content = hash_path.read_text(encoding="utf-8")
    if not content.strip():
        return set()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {relative_path(hash_path, root_dir)}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{relative_path(hash_path, root_dir)} must contain a JSON object.")
    return {key for key in data if isinstance(key, str)}


def build_records(source_dir, root_dir=ROOT_DIR):
    """Build audit records without modifying repository data."""
    root_path = Path(root_dir)
    existing_hashes = load_existing_hashes(root_path)
    records = []

    for image_path in find_image_files(source_dir):
        parse_result = parse_date_from_filename(image_path)
        range_status = RANGE_INVALID if parse_result.status == DATE_INVALID else classify_range(parse_result.value)
        target_path = None
        has_existing_target_conflict = False
        if parse_result.value is not None and range_status == RANGE_IN:
            target_path = build_target_path(parse_result.value)
            has_existing_target_conflict = (root_path / target_path).exists()

        file_hash = calculate_sha256(image_path)
        records.append(
            AuditRecord(
                source_path=image_path,
                source_display=image_path.resolve().as_posix(),
                date_status=parse_result.status,
                parsed_date=parse_result.value,
                range_status=range_status,
                target_path=target_path,
                sha256=file_hash,
                has_existing_target_conflict=has_existing_target_conflict,
                has_existing_hash_conflict=file_hash in existing_hashes,
            )
        )

    return sorted(records, key=record_sort_key)


def record_sort_key(record):
    """Sort records by parsed date first, then path for stable reports."""
    date_value = record.parsed_date.isoformat() if record.parsed_date is not None else "9999-99-99"
    return (date_value, record.source_display)


def find_duplicate_groups(records):
    """Find duplicate SHA256 groups across every supported history image."""
    by_hash = {}
    for record in records:
        by_hash.setdefault(record.sha256, []).append(record)

    groups = []
    for file_hash, grouped_records in by_hash.items():
        if len(grouped_records) < 2:
            continue
        groups.append(
            DuplicateGroup(
                sha256=file_hash,
                records=tuple(sorted(grouped_records, key=lambda record: record.source_display)),
            )
        )
    return sorted(groups, key=lambda group: group.sha256)


def run_audit(source_dir, root_dir=ROOT_DIR):
    """Run the read-only history audit and write reports/history_audit.md."""
    source_path = Path(source_dir).expanduser()
    if not source_path.exists() or not source_path.is_dir():
        raise ValueError(f"Source directory does not exist or is not a directory: {source_path}")

    root_path = Path(root_dir)
    print(f"Scanning source directory: {source_path.resolve().as_posix()}")
    records = build_records(source_path, root_path)
    duplicate_groups = find_duplicate_groups(records)
    report_content = build_report(source_path, records, duplicate_groups)
    report_path = root_path / "reports" / "history_audit.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_content, encoding="utf-8")

    print(f"Found supported image files: {len(records)}")
    print(f"Import candidates: {len(import_candidate_records(records))}")
    print(f"Unknown date files: {len(filter_records(records, date_status=DATE_UNKNOWN))}")
    print(f"Invalid date files: {len(filter_records(records, date_status=DATE_INVALID))}")
    print(f"Duplicate hash groups: {len(duplicate_groups)}")
    print(f"Wrote report: {relative_path(report_path, root_path)}")
    return report_path


def build_report(source_dir, records, duplicate_groups):
    """Build a stable Markdown audit report."""
    source_path = Path(source_dir).resolve().as_posix()
    import_candidates = import_candidate_records(records)
    unknown_records = filter_records(records, date_status=DATE_UNKNOWN)
    invalid_records = filter_records(records, date_status=DATE_INVALID)
    out_of_range_records = [
        record for record in records if record.range_status in {RANGE_BEFORE, RANGE_AFTER}
    ]
    existing_target_conflicts = [
        record for record in import_candidates if record.has_existing_target_conflict
    ]
    existing_hash_conflicts = [record for record in records if record.has_existing_hash_conflict]

    lines = [
        "# History Audit Report",
        "",
        "## Source Directory",
        "",
        f"- Path: {source_path}",
        "",
        "## Target Range",
        "",
        f"- Start: {TARGET_START_DATE.isoformat()}",
        f"- End: {TARGET_END_DATE.isoformat()}",
        "",
        "## Summary",
        "",
        markdown_table(
            ["Metric", "Count"],
            [
                ["Supported image files", str(len(records))],
                ["Import candidates", str(len(import_candidates))],
                ["Unknown date files", str(len(unknown_records))],
                ["Invalid date files", str(len(invalid_records))],
                ["Out-of-range files", str(len(out_of_range_records))],
                ["Duplicate hash groups", str(len(duplicate_groups))],
                ["Existing target conflicts", str(len(existing_target_conflicts))],
                ["Existing hash conflicts", str(len(existing_hash_conflicts))],
            ],
        ),
        "",
        "## Import Candidates",
        "",
        records_table(
            import_candidates,
            ["Date", "Source", "Target", "SHA256"],
            lambda record: [
                record.parsed_date.isoformat(),
                record.source_display,
                record.target_path or "",
                record.sha256,
            ],
        ),
        "",
        "## Unknown Date Files",
        "",
        records_table(
            unknown_records,
            ["Source", "SHA256"],
            lambda record: [record.source_display, record.sha256],
        ),
        "",
        "## Invalid Date Files",
        "",
        records_table(
            invalid_records,
            ["Source", "SHA256"],
            lambda record: [record.source_display, record.sha256],
        ),
        "",
        "## Out-of-Range Files",
        "",
        records_table(
            sorted(out_of_range_records, key=out_of_range_sort_key),
            ["Date", "Range", "Source", "SHA256"],
            lambda record: [
                record.parsed_date.isoformat(),
                record.range_status,
                record.source_display,
                record.sha256,
            ],
        ),
        "",
        "## Duplicate Files",
        "",
        duplicate_groups_table(duplicate_groups),
        "",
        "## Existing Target Conflicts",
        "",
        records_table(
            sorted(existing_target_conflicts, key=lambda record: record.target_path or ""),
            ["Date", "Source", "Target", "SHA256"],
            lambda record: [
                record.parsed_date.isoformat(),
                record.source_display,
                record.target_path or "",
                record.sha256,
            ],
        ),
        "",
        "## Existing Hash Conflicts",
        "",
        records_table(
            sorted(existing_hash_conflicts, key=lambda record: (record.sha256, record.source_display)),
            ["SHA256", "Source", "Target"],
            lambda record: [record.sha256, record.source_display, record.target_path or ""],
        ),
        "",
        "## Notes",
        "",
        "- This audit is read-only: it does not copy, delete, rename, or import wallpaper files.",
        "- This report is for pre-import review only and is not treated as formal archive data.",
        "- Target paths are repository-relative POSIX paths.",
        "",
    ]
    return "\n".join(lines)


def import_candidate_records(records):
    """Return valid in-range records sorted by date ascending."""
    return sorted(
        [record for record in records if record.range_status == RANGE_IN],
        key=lambda record: (record.parsed_date, record.source_display),
    )


def filter_records(records, date_status):
    """Return records matching a date parse status sorted by source path."""
    return sorted(
        [record for record in records if record.date_status == date_status],
        key=lambda record: record.source_display,
    )


def out_of_range_sort_key(record):
    """Sort out-of-range records by date and then path."""
    return (record.parsed_date or date.max, record.source_display)


def records_table(records, headers, row_builder):
    """Build a Markdown table for audit records."""
    rows = [row_builder(record) for record in records]
    return markdown_table(headers, rows)


def duplicate_groups_table(duplicate_groups):
    """Build a Markdown table for duplicate hash groups."""
    rows = []
    for group in duplicate_groups:
        source_files = "<br>".join(record.source_display for record in group.records)
        targets = "<br>".join(record.target_path or "" for record in group.records)
        rows.append([group.sha256, str(len(group.records)), source_files, targets])
    return markdown_table(["SHA256", "Count", "Source Files", "Target Paths"], rows)


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


def relative_path(path, root_dir=ROOT_DIR):
    """Return a POSIX path relative to the repository root."""
    return Path(path).relative_to(Path(root_dir)).as_posix()


def parse_args(argv=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a read-only audit for historical Bing wallpaper files."
    )
    parser.add_argument("source_dir", help="Directory containing historical wallpaper images.")
    return parser.parse_args(argv)


def main(argv=None):
    """Entry point for the history audit script."""
    args = parse_args(argv)
    try:
        run_audit(args.source_dir)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
