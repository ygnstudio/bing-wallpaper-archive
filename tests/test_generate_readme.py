import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "scripts" / "generate_readme.py"
SPEC = importlib.util.spec_from_file_location("generate_readme_script", SCRIPT_PATH)
generate_readme = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_readme)


class GenerateReadmeScriptTest(unittest.TestCase):
    def test_missing_index_file_loads_empty_records_with_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                records = generate_readme.load_index_records(Path(temp_dir))

            self.assertEqual(records, [])
            self.assertIn(
                "Warning: data/index.json not found. Generating README with empty records.",
                output.getvalue(),
            )

    def test_invalid_index_json_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            index_path = root_dir / "data" / "index.json"
            index_path.parent.mkdir(parents=True)
            index_path.write_text("{broken json", encoding="utf-8")

            with self.assertRaises(ValueError):
                generate_readme.load_index_records(root_dir)

    def test_validate_records_skips_missing_empty_absolute_and_non_posix_paths(self):
        records = [
            {
                "date": "2026-07-08",
                "image": "wallpapers/2026/07/20260708.jpg",
                "thumbnail": "thumbnails/2026/07/20260708.jpg",
            },
            {
                "date": "",
                "image": "wallpapers/2026/07/20260709.jpg",
                "thumbnail": "thumbnails/2026/07/20260709.jpg",
            },
            {
                "date": "2026-07-10",
                "image": "/absolute/wallpapers/2026/07/20260710.jpg",
                "thumbnail": "thumbnails/2026/07/20260710.jpg",
            },
            {
                "date": "2026-07-11",
                "image": "wallpapers\\2026\\07\\20260711.jpg",
                "thumbnail": "thumbnails/2026/07/20260711.jpg",
            },
            {
                "date": "2026-07-12",
                "image": "wallpapers/2026/07/20260712.jpg",
                "thumbnail": "",
            },
        ]
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            valid_records = generate_readme.validate_records(records)

        self.assertEqual(
            valid_records,
            [
                {
                    "date": "2026-07-08",
                    "title": "",
                    "copyright": "",
                    "image": "wallpapers/2026/07/20260708.jpg",
                    "thumbnail": "thumbnails/2026/07/20260708.jpg",
                }
            ],
        )
        self.assertIn("Warning: skipping invalid index record", output.getvalue())

    def test_build_readme_with_empty_records_has_complete_empty_state(self):
        content = generate_readme.build_readme([])

        self.assertIn("# Bing Wallpaper Archive", content)
        self.assertIn("## 最新壁纸\n\n暂无壁纸记录。", content)
        self.assertIn("## 最近壁纸\n\n暂无最近壁纸记录。", content)
        self.assertIn("归档总数：0", content)
        self.assertIn("起始日期：暂无", content)
        self.assertIn("最新日期：暂无", content)
        self.assertIn("## 功能范围", content)
        self.assertIn("## 项目边界", content)
        self.assertIn("## 目录结构", content)
        self.assertIn("## 自动化流程", content)
        self.assertIn("## 数据文件", content)

    def test_build_readme_with_one_record_has_latest_wallpaper(self):
        records = [self._record("2026-07-08")]

        content = generate_readme.build_readme(records)

        self.assertIn("## 最新壁纸", content)
        self.assertIn("**日期：** 2026-07-08", content)
        self.assertIn(
            "[![2026-07-08](thumbnails/2026/07/20260708.jpg)](wallpapers/2026/07/20260708.jpg)",
            content,
        )
        self.assertNotIn("%2F", content)
        self.assertIn("归档总数：1", content)
        self.assertIn("起始日期：2026-07-08", content)
        self.assertIn("最新日期：2026-07-08", content)

    def test_recent_wallpapers_are_limited_to_12_records(self):
        records = [self._record(f"2026-07-{day:02d}") for day in range(20, 5, -1)]

        recent_section = generate_readme.build_recent_section(records)

        self.assertEqual(recent_section.count("[!["), 12)
        self.assertIn("2026-07-20", recent_section)
        self.assertIn("2026-07-09", recent_section)
        self.assertNotIn("2026-07-08", recent_section)

    def test_write_readme_writes_utf8_with_final_newline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)

            generate_readme.write_readme("# 标题", root_dir)

            content = (root_dir / "README.md").read_text(encoding="utf-8")
            self.assertEqual(content, "# 标题\n")

    def test_generate_readme_does_not_modify_hash_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            data_dir = root_dir / "data"
            data_dir.mkdir(parents=True)
            (data_dir / "index.json").write_text(
                json.dumps([self._record("2026-07-08")], ensure_ascii=False),
                encoding="utf-8",
            )
            hash_path = data_dir / "hash.json"
            hash_path.write_text('{"abc": {"path": "x"}}\n', encoding="utf-8")

            generate_readme.generate_readme(root_dir)

            self.assertEqual(hash_path.read_text(encoding="utf-8"), '{"abc": {"path": "x"}}\n')
            self.assertTrue((root_dir / "README.md").read_text(encoding="utf-8").endswith("\n"))

    def _record(self, date_text):
        compact_date = date_text.replace("-", "")
        year, month = date_text[:4], date_text[5:7]
        return {
            "date": date_text,
            "title": "",
            "copyright": "",
            "image": f"wallpapers/{year}/{month}/{compact_date}.jpg",
            "thumbnail": f"thumbnails/{year}/{month}/{compact_date}.jpg",
        }


if __name__ == "__main__":
    unittest.main()
