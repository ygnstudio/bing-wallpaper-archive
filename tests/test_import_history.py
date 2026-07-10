import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "scripts" / "import_history.py"
SPEC = importlib.util.spec_from_file_location("import_history_script", SCRIPT_PATH)
import_history = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(import_history)
JPEG_A = b"\xff\xd8\xff\xe0same image"
JPEG_B = b"\xff\xd8\xff\xe0different image"


class ImportHistoryScriptTest(unittest.TestCase):
    def test_parse_date_from_filename_accepts_supported_formats(self):
        cases = {
            "20230501.jpg": date(2023, 5, 1),
            "2023-05-01.jpeg": date(2023, 5, 1),
            "2023_05_01.JPG": date(2023, 5, 1),
            "2023.05.01.JPEG": date(2023, 5, 1),
        }

        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                result = import_history.parse_date_from_filename(Path(filename))
                self.assertEqual(result.status, import_history.DATE_VALID)
                self.assertEqual(result.value, expected)

    def test_find_image_files_scans_visible_jpg_and_jpeg_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            visible_jpg = source_dir / "20230501.jpg"
            nested_jpeg = source_dir / "nested" / "20230502.JPEG"
            ignored_files = [
                source_dir / ".hidden.jpg",
                source_dir / ".ignored" / "20230503.jpg",
                source_dir / "20230504.png",
                source_dir / ".DS_Store",
                source_dir / ".gitkeep",
            ]
            for path in [visible_jpg, nested_jpeg, *ignored_files]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"image")

            images = import_history.find_image_files(source_dir)

            self.assertEqual(images, [visible_jpg, nested_jpeg])

    def test_build_target_path_uses_repo_relative_posix_path(self):
        target_path = import_history.build_target_path(date(2023, 5, 1))

        self.assertEqual(target_path, "wallpapers/2023/05/20230501.jpg")
        self.assertNotIn("\\", target_path)

    def test_import_history_imports_candidates_and_skips_later_duplicate_hashes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()
            source_contents = {
                "20230501.jpg": JPEG_A,
                "20230502.jpg": JPEG_A,
                "20230503.jpeg": JPEG_B,
                "20230231.jpg": b"\xff\xd8\xff\xe0invalid date",
                "daily.jpg": b"\xff\xd8\xff\xe0unknown date",
                "20230430.jpg": b"\xff\xd8\xff\xe0before range",
                "20260201.jpg": b"\xff\xd8\xff\xe0after range",
            }
            for filename, content in source_contents.items():
                (source_dir / filename).write_bytes(content)
            original_source_bytes = {
                path.name: path.read_bytes() for path in source_dir.iterdir() if path.is_file()
            }

            result = import_history.import_history(source_dir, root_dir)

            self.assertEqual(result.summary["total_source_images"], 7)
            self.assertEqual(result.summary["imported"], 2)
            self.assertEqual(result.summary["skipped_duplicate_hash"], 1)
            self.assertEqual(result.summary["skipped_invalid_date"], 1)
            self.assertEqual(result.summary["skipped_unknown_date"], 1)
            self.assertEqual(result.summary["skipped_out_of_range"], 2)
            self.assertEqual(
                (root_dir / "wallpapers" / "2023" / "05" / "20230501.jpg").read_bytes(),
                JPEG_A,
            )
            self.assertFalse(
                (root_dir / "wallpapers" / "2023" / "05" / "20230502.jpg").exists()
            )
            self.assertEqual(
                (root_dir / "wallpapers" / "2023" / "05" / "20230503.jpg").read_bytes(),
                JPEG_B,
            )

            hashes = json.loads((root_dir / "data" / "hash.json").read_text(encoding="utf-8"))
            metadata = json.loads(
                (root_dir / "data" / "metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(hashes), 2)
            self.assertEqual(metadata["2023-05-01"]["title"], "")
            self.assertEqual(metadata["2023-05-01"]["copyright"], "")
            self.assertEqual(
                metadata["2023-05-01"]["image"],
                "wallpapers/2023/05/20230501.jpg",
            )
            self.assertTrue((root_dir / "data" / "hash.json").read_bytes().endswith(b"\n"))
            self.assertTrue((root_dir / "data" / "metadata.json").read_bytes().endswith(b"\n"))
            self.assertFalse((root_dir / "data" / "hash.json.tmp").exists())
            self.assertFalse((root_dir / "data" / "metadata.json.tmp").exists())
            self.assertEqual(
                {path.name: path.read_bytes() for path in source_dir.iterdir() if path.is_file()},
                original_source_bytes,
            )

            report = (root_dir / "reports" / "history_import.md").read_text(encoding="utf-8")
            self.assertIn("# History Import Report", report)
            self.assertIn("wallpapers/2023/05/20230501.jpg", report)
            self.assertIn("wallpapers/2023/05/20230503.jpg", report)
            self.assertIn("wallpapers/2023/05/20230501.jpg", report)
            self.assertTrue(report.endswith("\n"))

    def test_existing_target_is_not_overwritten_and_hash_is_backfilled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()
            source_file = source_dir / "20230501.jpg"
            source_file.write_bytes(b"\xff\xd8\xff\xe0new source bytes")
            target_file = root_dir / "wallpapers" / "2023" / "05" / "20230501.jpg"
            target_file.parent.mkdir(parents=True)
            target_file.write_bytes(b"\xff\xd8\xff\xe0existing target bytes")

            result = import_history.import_history(source_dir, root_dir)

            self.assertEqual(result.summary["imported"], 0)
            self.assertEqual(result.summary["skipped_existing_target"], 1)
            self.assertEqual(target_file.read_bytes(), b"\xff\xd8\xff\xe0existing target bytes")
            existing_target_hash = import_history.calculate_sha256(target_file)
            hashes = json.loads((root_dir / "data" / "hash.json").read_text(encoding="utf-8"))
            self.assertIn(existing_target_hash, hashes)
            self.assertEqual(hashes[existing_target_hash]["path"], "wallpapers/2023/05/20230501.jpg")

    def test_existing_hash_skips_without_copying_new_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()
            source_file = source_dir / "20230501.jpg"
            source_file.write_bytes(b"\xff\xd8\xff\xe0known image")
            source_hash = import_history.calculate_sha256(source_file)
            hash_path = root_dir / "data" / "hash.json"
            hash_path.parent.mkdir(parents=True)
            hash_path.write_text(
                json.dumps(
                    {
                        source_hash: {
                            "date": "2023-04-01",
                            "path": "wallpapers/2023/04/20230401.jpg",
                            "url": "",
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = import_history.import_history(source_dir, root_dir)

            self.assertEqual(result.summary["imported"], 0)
            self.assertEqual(result.summary["skipped_existing_hash"], 1)
            self.assertFalse((root_dir / "wallpapers" / "2023" / "05" / "20230501.jpg").exists())
            report = (root_dir / "reports" / "history_import.md").read_text(encoding="utf-8")
            self.assertIn("wallpapers/2023/04/20230401.jpg", report)

    def test_existing_metadata_keeps_nonempty_title_and_copyright(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()
            source_dir.joinpath("20230501.jpg").write_bytes(b"\xff\xd8\xff\xe0image")
            metadata_path = root_dir / "data" / "metadata.json"
            metadata_path.parent.mkdir(parents=True)
            metadata_path.write_text(
                json.dumps(
                    {
                        "2023-05-01": {
                            "date": "2023-05-01",
                            "title": "Keep title",
                            "copyright": "Keep copyright",
                            "url": "https://www.bing.com/keep_1920x1080.jpg",
                            "image": "old/path.jpg",
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            import_history.import_history(source_dir, root_dir)

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["2023-05-01"]["title"], "Keep title")
            self.assertEqual(metadata["2023-05-01"]["copyright"], "Keep copyright")
            self.assertEqual(metadata["2023-05-01"]["url"], "https://www.bing.com/keep_1920x1080.jpg")
            self.assertEqual(metadata["2023-05-01"]["image"], "wallpapers/2023/05/20230501.jpg")

    def test_second_run_is_safe_and_reports_existing_targets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()
            source_dir.joinpath("20230501.jpg").write_bytes(b"\xff\xd8\xff\xe0image")

            first_result = import_history.import_history(source_dir, root_dir)
            second_result = import_history.import_history(source_dir, root_dir)

            self.assertEqual(first_result.summary["imported"], 1)
            self.assertEqual(second_result.summary["imported"], 0)
            self.assertEqual(second_result.summary["skipped_existing_target"], 1)
            hashes = json.loads((root_dir / "data" / "hash.json").read_text(encoding="utf-8"))
            self.assertEqual(len(hashes), 1)

    def test_empty_or_non_jpeg_source_is_skipped_before_copying(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            source_dir = Path(temp_dir) / "history"
            root_dir.mkdir()
            source_dir.mkdir()
            source_dir.joinpath("20230501.jpg").write_bytes(b"")
            source_dir.joinpath("20230502.jpg").write_bytes(b"not a jpeg")
            source_dir.joinpath("20230503.jpg").write_bytes(JPEG_A)

            result = import_history.import_history(source_dir, root_dir)

            self.assertEqual(result.summary["total_source_images"], 3)
            self.assertEqual(result.summary["imported"], 1)
            self.assertEqual(result.summary["skipped_invalid_image"], 2)
            self.assertFalse((root_dir / "wallpapers" / "2023" / "05" / "20230501.jpg").exists())
            self.assertFalse((root_dir / "wallpapers" / "2023" / "05" / "20230502.jpg").exists())
            report = (root_dir / "reports" / "history_import.md").read_text(encoding="utf-8")
            self.assertIn("## Skipped Invalid Image", report)
            self.assertIn("empty_or_non_jpeg", report)


if __name__ == "__main__":
    unittest.main()
