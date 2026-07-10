from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
INDEX_FILE = ROOT_DIR / "data" / "index.json"
README_FILE = ROOT_DIR / "README.md"
README_EN_FILE = ROOT_DIR / "README.en.md"
MAX_RECENT_WALLPAPERS = 12
PROJECT_VERSION = "v0.2.1"


def load_index_records(root_dir=ROOT_DIR):
    """Load data/index.json records, treating a missing file as empty."""
    root_path = Path(root_dir)
    index_path = root_path / "data" / "index.json"
    print("Reading index file: data/index.json")
    if not index_path.exists():
        print("Warning: data/index.json not found. Generating README with empty records.")
        return []

    try:
        records = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in data/index.json: {exc}") from exc

    if not isinstance(records, list):
        raise ValueError("data/index.json must contain a JSON array.")
    return records


def validate_records(records):
    """Validate index records and normalize optional fields."""
    valid_records = []
    for record in records:
        if not isinstance(record, dict):
            print("Warning: skipping invalid index record: record is not an object.")
            continue

        date_text = record.get("date")
        image_path = record.get("image")
        thumbnail_path = record.get("thumbnail")
        if not is_non_empty_string(date_text):
            print("Warning: skipping invalid index record: missing date.")
            continue
        if not is_valid_relative_posix_path(image_path):
            print("Warning: skipping invalid index record: invalid image path.")
            continue
        if not is_valid_relative_posix_path(thumbnail_path):
            print("Warning: skipping invalid index record: invalid thumbnail path.")
            continue

        valid_records.append(
            {
                "date": date_text,
                "title": record.get("title", "") if isinstance(record.get("title", ""), str) else "",
                "copyright": (
                    record.get("copyright", "")
                    if isinstance(record.get("copyright", ""), str)
                    else ""
                ),
                "image": image_path,
                "thumbnail": thumbnail_path,
            }
        )

    return valid_records


def is_non_empty_string(value):
    """Return whether a value is a non-empty string."""
    return isinstance(value, str) and bool(value.strip())


def is_valid_relative_posix_path(value):
    """Return whether a Markdown path is relative, non-empty, and POSIX style."""
    if not is_non_empty_string(value):
        return False
    if "\\" in value:
        return False
    path = Path(value)
    if path.is_absolute():
        return False
    return True


def build_latest_section(records, language="zh"):
    """Build the latest wallpaper README section."""
    labels = labels_for(language)
    if not records:
        return f"## {labels['latest_heading']}\n\n{labels['empty_latest']}"

    latest = records[0]
    lines = [
        f"## {labels['latest_heading']}",
        "",
        f"**{labels['date']}** {latest['date']}",
    ]
    if latest["title"]:
        lines.extend(["", f"**{labels['title']}** {latest['title']}"])
    if latest["copyright"]:
        lines.extend(["", f"**{labels['copyright']}** {latest['copyright']}"])
    lines.extend(
        [
            "",
            build_image_link(latest),
        ]
    )
    return "\n".join(lines)


def build_recent_section(records, language="zh"):
    """Build a table with at most 12 recent wallpapers."""
    labels = labels_for(language)
    if not records:
        return f"## {labels['recent_heading']}\n\n{labels['empty_recent']}"

    lines = [
        f"## {labels['recent_heading']}",
        "",
        f"| {labels['date_column']} | {labels['preview_column']} |",
        "|---|---|",
    ]
    for record in records[:MAX_RECENT_WALLPAPERS]:
        lines.append(f"| {record['date']} | {build_image_link(record)} |")
    return "\n".join(lines)


def build_stats_section(records, language="zh"):
    """Build archive statistics from validated records."""
    labels = labels_for(language)
    if not records:
        total = 0
        start_date = labels["none"]
        latest_date = labels["none"]
    else:
        dates = [record["date"] for record in records]
        total = len(records)
        start_date = min(dates)
        latest_date = max(dates)

    return "\n".join(
        [
            f"## {labels['status_heading']}",
            "",
            f"- {labels['status']}: Active",
            f"- {labels['version']}: {PROJECT_VERSION}",
            f"- {labels['images']}: {total}",
            f"- {labels['thumbnails']}: {total}",
            f"- {labels['metadata_records']}: {total}",
            f"- {labels['date_range']}: {start_date} - {latest_date}",
        ]
    )


def build_image_link(record):
    """Build a relative Markdown image link without URL encoding."""
    date_text = record["date"]
    return f"[![{date_text}]({record['thumbnail']})]({record['image']})"


def build_readme(records, language="zh"):
    """Build the full README content from validated index records."""
    sections = [
        build_intro_section(language),
        build_stats_section(records, language),
        build_latest_section(records, language),
        build_recent_section(records, language),
        build_maintenance_section(language),
        build_data_files_section(language),
        "## License\n\nMIT",
    ]
    return "\n\n---\n\n".join(sections)


def build_intro_section(language="zh"):
    """Build the README introduction."""
    if language == "en":
        return "\n\n".join(
            [
                "# Bing Wallpaper Archive",
                "[中文](README.md) | English",
                (
                    "Bing Wallpaper Archive is a personal archive for daily Bing 1080P "
                    "wallpapers. It stores original images, thumbnails, metadata, and an "
                    "index, then updates through GitHub Actions."
                ),
            ]
        )

    return "\n\n".join(
        [
            "# Bing Wallpaper Archive",
            "中文 | [English](README.en.md)",
            (
                "Bing Wallpaper Archive 是一个个人自用的 Bing 1080P 壁纸自动归档项目。"
                "它保存原图、缩略图、metadata 和索引数据，并通过 GitHub Actions 每日更新。"
            ),
        ]
    )


def build_maintenance_section(language="zh"):
    """Build the long-term maintenance section."""
    if language == "en":
        return "\n".join(
            [
                "## Maintenance",
                "",
                "Current maintained features:",
                "",
                "- Daily Bing 1080P wallpaper download",
                "- Thumbnail generation",
                "- Metadata, hash, and index storage",
                "- README generation",
                "- Archive integrity checking",
                "",
                "Historical migration tools were removed after archive completion.",
            ]
        )

    return "\n".join(
        [
            "## 维护",
            "",
            "当前保留的长期功能：",
            "",
            "- 每日下载 Bing 1080P 壁纸",
            "- 生成缩略图",
            "- 保存 metadata、hash 和 index",
            "- 自动生成 README",
            "- 检查归档完整性",
            "",
            "历史迁移工具已在归档完成后移除。",
        ]
    )


def build_data_files_section(language="zh"):
    """Build the data files section."""
    if language == "en":
        return "\n".join(
            [
                "## Data",
                "",
                "- Original images: `wallpapers/YYYY/MM/YYYYMMDD.jpg`",
                "- Thumbnails: `thumbnails/YYYY/MM/YYYYMMDD.jpg`",
                "- Index: `data/index.json`",
                "- Hash records: `data/hash.json`",
                "- Metadata records: `data/metadata.json`",
                "- Health report: `reports/archive_check.md`",
                "",
                "Run locally:",
                "",
                "```bash",
                "python3 -m unittest discover -s tests -v",
                "python3 scripts/check_archive.py",
                "```",
            ]
        )

    return "\n".join(
        [
            "## 数据",
            "",
            "- 原图：`wallpapers/YYYY/MM/YYYYMMDD.jpg`",
            "- 缩略图：`thumbnails/YYYY/MM/YYYYMMDD.jpg`",
            "- 索引：`data/index.json`",
            "- Hash 记录：`data/hash.json`",
            "- Metadata 记录：`data/metadata.json`",
            "- 健康检查报告：`reports/archive_check.md`",
            "",
            "本地验证：",
            "",
            "```bash",
            "python3 -m unittest discover -s tests -v",
            "python3 scripts/check_archive.py",
            "```",
        ]
    )


def labels_for(language):
    """Return labels for README generation."""
    if language == "en":
        return {
            "latest_heading": "Latest Wallpaper",
            "recent_heading": "Recent Wallpapers",
            "status_heading": "Status",
            "empty_latest": "No wallpaper records yet.",
            "empty_recent": "No recent wallpaper records yet.",
            "date": "Date:",
            "title": "Title:",
            "copyright": "Copyright:",
            "date_column": "Date",
            "preview_column": "Preview",
            "none": "N/A",
            "status": "Status",
            "version": "Version",
            "images": "Images",
            "thumbnails": "Thumbnails",
            "metadata_records": "Metadata records",
            "date_range": "Date range",
        }

    return {
        "latest_heading": "最新壁纸",
        "recent_heading": "最近壁纸",
        "status_heading": "状态",
        "empty_latest": "暂无壁纸记录。",
        "empty_recent": "暂无最近壁纸记录。",
        "date": "日期：",
        "title": "标题：",
        "copyright": "版权：",
        "date_column": "日期",
        "preview_column": "预览",
        "none": "暂无",
        "status": "状态",
        "version": "版本",
        "images": "图片",
        "thumbnails": "缩略图",
        "metadata_records": "Metadata 记录",
        "date_range": "日期范围",
    }


def write_readme(content, root_dir=ROOT_DIR, filename="README.md"):
    """Write a README file with UTF-8 encoding and a final newline."""
    readme_path = Path(root_dir) / filename
    readme_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return readme_path


def generate_readme(root_dir=ROOT_DIR):
    """Generate Chinese and English README files from data/index.json."""
    root_path = Path(root_dir)
    raw_records = load_index_records(root_path)
    records = validate_records(raw_records)
    if records:
        print(f"Loaded {len(records)} wallpaper records.")
    else:
        print("No wallpaper records found.")

    write_readme(build_readme(records, language="zh"), root_path, "README.md")
    write_readme(build_readme(records, language="en"), root_path, "README.en.md")
    print("Generated README.md")
    print("Generated README.en.md")
    return records


def main():
    """Entry point for generating README content."""
    try:
        generate_readme()
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}") from exc


if __name__ == "__main__":
    main()
