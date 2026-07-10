import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "scripts" / "check_archive.py"
SPEC = importlib.util.spec_from_file_location("check_archive_script", SCRIPT_PATH)
check_archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_archive)


class CheckArchiveScriptTest(unittest.TestCase):
    def test_normal_archive_returns_zero_writes_report_and_preserves_data_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            build_complete_archive(root_dir, ["2023-05-01", "2023-05-02"])
            before_data = read_data_files(root_dir)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = check_archive.main(root_dir)

            self.assertEqual(exit_code, 0)
            self.assertEqual(read_data_files(root_dir), before_data)
            report = root_dir / "reports" / "archive_check.md"
            self.assertTrue(report.exists())
            content = report.read_text(encoding="utf-8")
            self.assertIn("# Archive Check Report", content)
            self.assertIn("- Status: OK", content)
            self.assertIn("- Errors: 0", content)
            self.assertIn("- Wallpapers: 2", content)
            self.assertIn("Archive check status: OK", output.getvalue())

    def test_non_standard_wallpaper_path_is_reported_as_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            build_complete_archive(root_dir, ["2023-05-01"])
            invalid_path = root_dir / "wallpapers" / "2023" / "5" / "20230502.jpg"
            write_jpeg(invalid_path)

            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "wallpaper_path", "wallpapers/2023/5/20230502.jpg")
            self.assertEqual(result.summary["status"], "FAILED")

    def test_missing_thumbnail_is_error_and_extra_thumbnail_is_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            build_complete_archive(root_dir, ["2023-05-01"])
            missing_thumbnail = root_dir / "thumbnails" / "2023" / "05" / "20230501.jpg"
            missing_thumbnail.unlink()
            extra_thumbnail = root_dir / "thumbnails" / "2023" / "05" / "20230502.jpg"
            write_jpeg(extra_thumbnail)

            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "missing_thumbnail", "wallpapers/2023/05/20230501.jpg")
            self.assertHasIssue(result.warnings, "extra_thumbnail", "thumbnails/2023/05/20230502.jpg")
            self.assertEqual(
                result.missing_thumbnails,
                (("wallpapers/2023/05/20230501.jpg", "thumbnails/2023/05/20230501.jpg"),),
            )

    def test_index_missing_path_and_invalid_json_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            build_complete_archive(root_dir, ["2023-05-01"])
            index_path = root_dir / "data" / "index.json"
            records = json.loads(index_path.read_text(encoding="utf-8"))
            records[0]["image"] = "wallpapers/2023/05/missing.jpg"
            write_json(index_path, records)

            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "index_image", "wallpapers/2023/05/missing.jpg")
            self.assertHasIssue(
                result.errors,
                "index_missing_wallpaper",
                "wallpapers/2023/05/20230501.jpg",
            )

            index_path.write_text("{broken json", encoding="utf-8")
            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "json_invalid", "data/index.json")

    def test_hash_missing_and_mismatch_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            build_complete_archive(root_dir, ["2023-05-01"])
            hash_path = root_dir / "data" / "hash.json"
            write_json(hash_path, {})

            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "hash_missing", "wallpapers/2023/05/20230501.jpg")

            write_json(
                hash_path,
                {
                    "0" * 64: {
                        "date": "2023-05-01",
                        "path": "wallpapers/2023/05/20230501.jpg",
                        "url": "",
                    }
                },
            )
            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "hash_mismatch", "wallpapers/2023/05/20230501.jpg")

    def test_metadata_missing_and_invalid_image_path_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            build_complete_archive(root_dir, ["2023-05-01"])
            metadata_path = root_dir / "data" / "metadata.json"
            write_json(metadata_path, {})

            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "metadata_missing", "wallpapers/2023/05/20230501.jpg")

            write_json(
                metadata_path,
                {
                    "2023-05-01": {
                        "date": "2023-05-01",
                        "title": "",
                        "copyright": "",
                        "image": "/absolute/path.jpg",
                    }
                },
            )
            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "metadata_image", "data/metadata.json[2023-05-01]")

    def test_duplicate_hash_is_reported_without_deleting_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            paths = build_complete_archive(root_dir, ["2023-05-01", "2023-05-02"])
            second_wallpaper = paths["wallpapers/2023/05/20230502.jpg"]
            second_wallpaper.write_bytes(paths["wallpapers/2023/05/20230501.jpg"].read_bytes())

            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "duplicate_hash", "wallpapers/2023/05/20230501.jpg")
            self.assertEqual(len(result.duplicate_hashes), 1)
            self.assertTrue(paths["wallpapers/2023/05/20230501.jpg"].exists())
            self.assertTrue(paths["wallpapers/2023/05/20230502.jpg"].exists())

    def test_zero_byte_image_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            paths = build_complete_archive(root_dir, ["2023-05-01"])
            paths["thumbnails/2023/05/20230501.jpg"].write_bytes(b"")

            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "zero_byte", "thumbnails/2023/05/20230501.jpg")

    def test_damaged_image_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            paths = build_complete_archive(root_dir, ["2023-05-01"])
            paths["wallpapers/2023/05/20230501.jpg"].write_bytes(b"not a valid jpeg")

            result = check_archive.run_archive_check(root_dir)

            self.assertHasIssue(result.errors, "image_unreadable", "wallpapers/2023/05/20230501.jpg")

    def test_error_return_code_is_one(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir) / "repo"
            root_dir.mkdir()
            build_complete_archive(root_dir, ["2023-05-01"])
            (root_dir / "data" / "metadata.json").unlink()

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = check_archive.main(root_dir)

            self.assertEqual(exit_code, 1)
            self.assertIn("Archive check status: FAILED", output.getvalue())

    def assertHasIssue(self, issues, issue_type, path_fragment):
        self.assertTrue(
            any(issue.type == issue_type and path_fragment in issue.path for issue in issues),
            f"Expected issue {issue_type!r} containing {path_fragment!r}; got {issues!r}",
        )


def build_complete_archive(root_dir, date_strings):
    paths = {}
    index_records = []
    hash_records = {}
    metadata_records = {}

    for date_string in date_strings:
        wallpaper_date = date.fromisoformat(date_string)
        compact_date = wallpaper_date.strftime("%Y%m%d")
        image_rel = f"wallpapers/{wallpaper_date.year:04d}/{wallpaper_date.month:02d}/{compact_date}.jpg"
        thumbnail_rel = f"thumbnails/{wallpaper_date.year:04d}/{wallpaper_date.month:02d}/{compact_date}.jpg"
        image_path = root_dir / image_rel
        thumbnail_path = root_dir / thumbnail_rel
        write_jpeg(image_path, color=color_for_date(wallpaper_date))
        write_jpeg(thumbnail_path, color=color_for_date(wallpaper_date, offset=64))
        paths[image_rel] = image_path
        paths[thumbnail_rel] = thumbnail_path

        image_hash = check_archive.calculate_sha256(image_path)
        hash_records[image_hash] = {
            "date": date_string,
            "path": image_rel,
            "url": "",
        }
        metadata_records[date_string] = {
            "date": date_string,
            "title": "",
            "copyright": "",
            "url": "",
            "image": image_rel,
        }
        index_records.append(
            {
                "date": date_string,
                "title": "",
                "copyright": "",
                "image": image_rel,
                "thumbnail": thumbnail_rel,
            }
        )

    data_dir = root_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    write_json(data_dir / "hash.json", hash_records)
    write_json(data_dir / "metadata.json", metadata_records)
    write_json(data_dir / "index.json", sorted(index_records, key=lambda item: item["date"], reverse=True))
    return paths


def write_jpeg(path, color=(32, 96, 160)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color=color).save(path, format="JPEG")


def color_for_date(value, offset=0):
    base = value.toordinal() + offset
    return (base % 255, (base * 3) % 255, (base * 7) % 255)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_data_files(root_dir):
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted((root_dir / "data").glob("*.json"))
    }


if __name__ == "__main__":
    unittest.main()
