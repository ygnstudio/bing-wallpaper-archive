import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "scripts" / "audit_history.py"
SPEC = importlib.util.spec_from_file_location("audit_history_script", SCRIPT_PATH)
audit_history = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_history)


class AuditHistoryScriptTest(unittest.TestCase):
    def test_parse_date_from_filename_accepts_supported_formats(self):
        cases = {
            "20230501.jpg": date(2023, 5, 1),
            "2023-05-01.jpeg": date(2023, 5, 1),
            "2023_05_01.JPG": date(2023, 5, 1),
            "2023.05.01.JPEG": date(2023, 5, 1),
        }

        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                result = audit_history.parse_date_from_filename(Path(filename))
                self.assertEqual(result.status, audit_history.DATE_VALID)
                self.assertEqual(result.value, expected)

    def test_parse_date_from_filename_distinguishes_unknown_and_invalid_dates(self):
        unknown = audit_history.parse_date_from_filename(Path("bing-wallpaper.jpg"))
        invalid = audit_history.parse_date_from_filename(Path("20230231.jpg"))

        self.assertEqual(unknown.status, audit_history.DATE_UNKNOWN)
        self.assertIsNone(unknown.value)
        self.assertEqual(invalid.status, audit_history.DATE_INVALID)
        self.assertIsNone(invalid.value)

    def test_find_image_files_scans_supported_visible_jpg_and_jpeg_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            visible_jpg = source_dir / "20230501.jpg"
            nested_jpeg = source_dir / "nested" / "20230502.JPEG"
            hidden_file = source_dir / ".hidden.jpg"
            hidden_dir_file = source_dir / ".ignored" / "20230503.jpg"
            png_file = source_dir / "20230504.png"
            ds_store = source_dir / ".DS_Store"
            gitkeep = source_dir / ".gitkeep"
            for path in [
                visible_jpg,
                nested_jpeg,
                hidden_file,
                hidden_dir_file,
                png_file,
                ds_store,
                gitkeep,
            ]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"image")

            images = audit_history.find_image_files(source_dir)

            self.assertEqual(images, [visible_jpg, nested_jpeg])

    def test_build_target_path_uses_repo_relative_posix_path(self):
        target_path = audit_history.build_target_path(date(2023, 5, 1))

        self.assertEqual(target_path, "wallpapers/2023/05/20230501.jpg")
        self.assertNotIn("\\", target_path)

    def test_build_records_classifies_date_ranges_and_existing_conflicts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()

            in_range = source_dir / "20230501.jpg"
            before_range = source_dir / "20230430.jpg"
            after_range = source_dir / "20260201.jpg"
            unknown = source_dir / "daily.jpg"
            invalid = source_dir / "20230231.jpg"
            for path in [in_range, before_range, after_range, unknown, invalid]:
                path.write_bytes(path.name.encode("utf-8"))

            existing_target = root_dir / "wallpapers" / "2023" / "05" / "20230501.jpg"
            existing_target.parent.mkdir(parents=True)
            existing_target.write_bytes(b"already in repo")
            existing_hash = audit_history.calculate_sha256(in_range)
            hash_path = root_dir / "data" / "hash.json"
            hash_path.parent.mkdir(parents=True)
            hash_path.write_text(
                json.dumps(
                    {
                        existing_hash: {
                            "date": "2023-05-01",
                            "path": "wallpapers/2023/05/20230501.jpg",
                        }
                    }
                ),
                encoding="utf-8",
            )

            records = audit_history.build_records(source_dir, root_dir)
            by_name = {record.source_path.name: record for record in records}

            self.assertEqual(by_name["20230501.jpg"].date_status, audit_history.DATE_VALID)
            self.assertEqual(by_name["20230501.jpg"].range_status, audit_history.RANGE_IN)
            self.assertEqual(
                by_name["20230501.jpg"].target_path,
                "wallpapers/2023/05/20230501.jpg",
            )
            self.assertTrue(by_name["20230501.jpg"].has_existing_target_conflict)
            self.assertTrue(by_name["20230501.jpg"].has_existing_hash_conflict)
            self.assertEqual(by_name["20230430.jpg"].range_status, audit_history.RANGE_BEFORE)
            self.assertEqual(by_name["20260201.jpg"].range_status, audit_history.RANGE_AFTER)
            self.assertEqual(by_name["daily.jpg"].date_status, audit_history.DATE_UNKNOWN)
            self.assertEqual(by_name["20230231.jpg"].date_status, audit_history.DATE_INVALID)

    def test_duplicate_groups_include_all_supported_history_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()

            in_range = source_dir / "20230501.jpg"
            out_of_range = source_dir / "20200101.jpg"
            unknown = source_dir / "daily-wallpaper.jpeg"
            different = source_dir / "20230502.jpg"
            for path in [in_range, out_of_range, unknown]:
                path.write_bytes(b"same bytes")
            different.write_bytes(b"different bytes")

            records = audit_history.build_records(source_dir, root_dir)
            duplicate_groups = audit_history.find_duplicate_groups(records)

            self.assertEqual(len(duplicate_groups), 1)
            self.assertEqual(
                {Path(record.source_display).name for record in duplicate_groups[0].records},
                {"20230501.jpg", "20200101.jpg", "daily-wallpaper.jpeg"},
            )

    def test_generate_report_contains_required_sections_and_readable_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()

            candidate = source_dir / "20230501.jpg"
            invalid = source_dir / "20230231.jpg"
            duplicate = source_dir / "copy-of-candidate.jpeg"
            candidate.write_bytes(b"same bytes")
            invalid.write_bytes(b"invalid bytes")
            duplicate.write_bytes(b"same bytes")

            report_path = audit_history.run_audit(source_dir, root_dir)
            content = report_path.read_text(encoding="utf-8")

            for heading in [
                "# History Audit Report",
                "## Source Directory",
                "## Target Range",
                "## Summary",
                "## Import Candidates",
                "## Unknown Date Files",
                "## Invalid Date Files",
                "## Out-of-Range Files",
                "## Duplicate Files",
                "## Existing Target Conflicts",
                "## Existing Hash Conflicts",
                "## Notes",
            ]:
                self.assertIn(heading, content)
            self.assertIn("wallpapers/2023/05/20230501.jpg", content)
            self.assertIn(candidate.resolve().as_posix(), content)
            self.assertIn(invalid.resolve().as_posix(), content)
            self.assertIn("copy-of-candidate.jpeg", content)
            self.assertTrue(content.endswith("\n"))

    def test_run_audit_writes_only_report_and_leaves_formal_data_unchanged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()
            source_dir.joinpath("20230501.jpg").write_bytes(b"image")
            data_dir = root_dir / "data"
            data_dir.mkdir()
            official_files = {
                root_dir / "data" / "index.json": "[]\n",
                root_dir / "data" / "hash.json": "{}\n",
                root_dir / "data" / "metadata.json": "{}\n",
                root_dir / "README.md": "# README\n",
            }
            for path, content in official_files.items():
                path.write_text(content, encoding="utf-8")
            root_dir.joinpath("wallpapers").mkdir()
            root_dir.joinpath("thumbnails").mkdir()

            report_path = audit_history.run_audit(source_dir, root_dir)

            self.assertEqual(report_path, root_dir / "reports" / "history_audit.md")
            self.assertTrue(report_path.exists())
            for path, content in official_files.items():
                self.assertEqual(path.read_text(encoding="utf-8"), content)
            self.assertEqual(list((root_dir / "wallpapers").iterdir()), [])
            self.assertEqual(list((root_dir / "thumbnails").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
