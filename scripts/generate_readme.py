from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
INDEX_FILE = ROOT_DIR / "data" / "index.json"
README_FILE = ROOT_DIR / "README.md"
MAX_RECENT_WALLPAPERS = 12


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


def build_latest_section(records):
    """Build the latest wallpaper README section."""
    if not records:
        return "## 最新壁纸\n\n暂无壁纸记录。"

    latest = records[0]
    lines = [
        "## 最新壁纸",
        "",
        f"**日期：** {latest['date']}",
    ]
    if latest["title"]:
        lines.extend(["", f"**标题：** {latest['title']}"])
    if latest["copyright"]:
        lines.extend(["", f"**版权：** {latest['copyright']}"])
    lines.extend(
        [
            "",
            build_image_link(latest),
        ]
    )
    return "\n".join(lines)


def build_recent_section(records):
    """Build a table with at most 12 recent wallpapers."""
    if not records:
        return "## 最近壁纸\n\n暂无最近壁纸记录。"

    lines = [
        "## 最近壁纸",
        "",
        "| 日期 | 预览 |",
        "|---|---|",
    ]
    for record in records[:MAX_RECENT_WALLPAPERS]:
        lines.append(f"| {record['date']} | {build_image_link(record)} |")
    return "\n".join(lines)


def build_stats_section(records):
    """Build archive statistics from validated records."""
    if not records:
        total = 0
        start_date = "暂无"
        latest_date = "暂无"
    else:
        dates = [record["date"] for record in records]
        total = len(records)
        start_date = min(dates)
        latest_date = max(dates)

    return "\n".join(
        [
            "## 归档统计",
            "",
            f"- 归档总数：{total}",
            f"- 起始日期：{start_date}",
            f"- 最新日期：{latest_date}",
        ]
    )


def build_image_link(record):
    """Build a relative Markdown image link without URL encoding."""
    date_text = record["date"]
    return f"[![{date_text}]({record['thumbnail']})]({record['image']})"


def build_readme(records):
    """Build the full README content from validated index records."""
    sections = [
        build_intro_section(),
        build_status_section(),
        build_latest_section(records),
        build_recent_section(records),
        build_stats_section(records),
        build_scope_section(),
        build_boundaries_section(),
        build_directory_section(),
        build_automation_section(),
        build_data_files_section(),
        "## License\n\nMIT",
    ]
    return "\n\n---\n\n".join(sections)


def build_intro_section():
    """Build the README introduction."""
    return "\n\n".join(
        [
            "# Bing Wallpaper Archive",
            "Bing Wallpaper Archive 是一个个人自用的 Bing 壁纸自动归档项目。",
            (
                "项目会自动归档每日 Bing 1080P 壁纸，并生成缩略图、索引数据和 README "
                "展示内容。后续该项目会接入 `ygnstudio.github.io`，作为雁归南 Studio "
                "官网中的一个项目展示内容。"
            ),
        ]
    )


def build_status_section():
    """Build the current status section."""
    return "\n".join(
        [
            "## 当前状态",
            "",
            "当前版本：",
            "",
            "```text",
            "v0.1.0",
            "```",
            "",
            "当前阶段：",
            "",
            "```text",
            "自动化归档脚本实现",
            "```",
        ]
    )


def build_scope_section():
    """Build the project scope section."""
    return "\n".join(
        [
            "## 功能范围",
            "",
            "本项目包含：",
            "",
            "- 每日自动获取 Bing 1080P 壁纸。",
            "- 按年月归档图片。",
            "- 生成缩略图。",
            "- 生成 `data/index.json`。",
            "- 使用 `data/hash.json` 做去重。",
            "- 自动更新 README。",
            "- 使用 GitHub Actions 定时运行。",
            "- 后续接入个人官网展示。",
        ]
    )


def build_boundaries_section():
    """Build the project boundaries section."""
    return "\n".join(
        [
            "## 项目边界",
            "",
            "本项目长期不包含以下内容：",
            "",
            "- UHD / 4K 版本保存。",
            "- 多分辨率版本管理。",
            "- 复杂前端图库。",
            "- 多语言站点。",
            "- 用户登录。",
            "- 搜索系统。",
            "- 数据库。",
            "- 商业化。",
            "- 多人协作后台。",
            "- 多地区壁纸源。",
            "- 高级图片标签系统。",
            "",
            "保留这些边界的原因：",
            "",
            "- 项目主要服务于个人自动归档需求。",
            "- 只保存 1080P 版本，降低仓库体积和维护成本。",
            "- 展示需求由 README 和未来的个人官网承担。",
            "- 不引入数据库、登录、多用户等会显著增加复杂度的功能。",
        ]
    )


def build_directory_section():
    """Build the directory structure section."""
    return "\n".join(
        [
            "## 目录结构",
            "",
            "```text",
            "bing-wallpaper-archive/",
            "  .github/",
            "    workflows/",
            "      update.yml",
            "",
            "  data/",
            "    index.json",
            "    hash.json",
            "",
            "  scripts/",
            "    download.py",
            "    generate_thumbnail.py",
            "    generate_index.py",
            "    generate_readme.py",
            "",
            "  wallpapers/",
            "    YYYY/",
            "      MM/",
            "        YYYYMMDD.jpg",
            "",
            "  thumbnails/",
            "    YYYY/",
            "      MM/",
            "        YYYYMMDD.jpg",
            "",
            "  README.md",
            "  project.json",
            "  requirements.txt",
            "```",
        ]
    )


def build_automation_section():
    """Build the automation flow section."""
    return "\n".join(
        [
            "## 自动化流程",
            "",
            "GitHub Actions 按以下流程运行：",
            "",
            "```text",
            "Checkout",
            "↓",
            "设置 Python 环境",
            "↓",
            "安装依赖",
            "↓",
            "下载 1080P 壁纸",
            "↓",
            "生成缩略图",
            "↓",
            "更新 index.json",
            "↓",
            "更新 README",
            "↓",
            "检测变更",
            "↓",
            "Commit",
            "↓",
            "Push",
            "```",
        ]
    )


def build_data_files_section():
    """Build the data files section."""
    return "\n".join(
        [
            "## 数据文件",
            "",
            "### `data/index.json`",
            "",
            "用于记录壁纸索引。",
            "",
            "每条记录格式：",
            "",
            "```json",
            "{",
            '  "date": "2026-07-08",',
            '  "title": "",',
            '  "copyright": "",',
            '  "image": "wallpapers/2026/07/20260708.jpg",',
            '  "thumbnail": "thumbnails/2026/07/20260708.jpg"',
            "}",
            "```",
            "",
            "### `data/hash.json`",
            "",
            "用于记录图片 SHA256 哈希，避免重复保存。",
        ]
    )


def write_readme(content, root_dir=ROOT_DIR):
    """Write README.md with UTF-8 encoding and a final newline."""
    readme_path = Path(root_dir) / "README.md"
    readme_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return readme_path


def generate_readme(root_dir=ROOT_DIR):
    """Generate README.md from data/index.json."""
    root_path = Path(root_dir)
    raw_records = load_index_records(root_path)
    records = validate_records(raw_records)
    if records:
        print(f"Loaded {len(records)} wallpaper records.")
    else:
        print("No wallpaper records found.")

    content = build_readme(records)
    write_readme(content, root_path)
    print("Generated README.md")
    return records


def main():
    """Entry point for generating README content."""
    try:
        generate_readme()
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}") from exc


if __name__ == "__main__":
    main()
