import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "scripts" / "download.py"
SPEC = importlib.util.spec_from_file_location("download_script", SCRIPT_PATH)
download = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(download)


class DownloadScriptTest(unittest.TestCase):
    def test_build_image_url_uses_bing_base_and_1080p(self):
        metadata = {
            "url": "/th?id=OHR.Example_UHD.jpg&rf=Example_3840x2160.jpg&pid=hp"
        }

        image_url = download.build_image_url(metadata)

        self.assertEqual(
            image_url,
            "https://www.bing.com/th?id=OHR.Example_1920x1080.jpg&rf=Example_1920x1080.jpg&pid=hp",
        )
        self.assertIn("1920x1080", image_url)
        self.assertNotIn("UHD", image_url)
        self.assertNotIn("3840x2160", image_url)
        self.assertNotIn("4K", image_url)

    def test_get_wallpaper_date_uses_startdate_then_today_fallback(self):
        self.assertEqual(
            download.get_wallpaper_date({"startdate": "20260708"}),
            date(2026, 7, 8),
        )
        self.assertEqual(
            download.get_wallpaper_date({}, today=date(2026, 7, 9)),
            date(2026, 7, 9),
        )

    def test_get_wallpaper_path_uses_year_month_and_yyyymmdd(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)

            wallpaper_path = download.get_wallpaper_path(date(2026, 7, 8), root_dir)

            self.assertEqual(
                wallpaper_path,
                root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg",
            )

    def test_hash_json_read_write_handles_missing_empty_and_invalid_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            hash_file = Path(temp_dir) / "data" / "hash.json"

            self.assertEqual(download.load_hashes(hash_file), {})

            hash_file.parent.mkdir(parents=True)
            hash_file.write_text("", encoding="utf-8")
            self.assertEqual(download.load_hashes(hash_file), {})

            hashes = {
                "abc123": {
                    "date": "2026-07-08",
                    "path": "wallpapers/2026/07/20260708.jpg",
                    "url": "https://www.bing.com/th?id=OHR.Example_1920x1080.jpg",
                }
            }
            download.save_hashes(hash_file, hashes)
            self.assertEqual(download.load_hashes(hash_file), hashes)

            hash_file.write_text("{broken json", encoding="utf-8")
            with self.assertRaises(ValueError):
                download.load_hashes(hash_file)

    def test_existing_file_with_hash_record_skips_without_download(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            metadata = self._metadata()
            target_path = download.get_wallpaper_path(date(2026, 7, 8), root_dir)
            target_path.parent.mkdir(parents=True)
            content = b"existing wallpaper"
            target_path.write_bytes(content)
            hash_value = download.calculate_sha256(content)
            hash_file = download.get_hash_file(root_dir)
            download.save_hashes(
                hash_file,
                {
                    hash_value: {
                        "date": "2026-07-08",
                        "path": "wallpapers/2026/07/20260708.jpg",
                        "url": "https://www.bing.com/th?id=OHR.Example_1920x1080.jpg&pid=hp",
                    }
                },
            )

            def fail_downloader(_url):
                self.fail("Downloader should not be called when target file exists.")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = download.process_wallpaper(
                    metadata,
                    root_dir=root_dir,
                    downloader=fail_downloader,
                    today=date(2026, 7, 9),
                )

            self.assertEqual(result, download.STATUS_EXISTS)
            self.assertIn("Target wallpaper already exists, skipping", output.getvalue())

    def test_existing_file_with_missing_hash_backfills_hash_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            metadata = self._metadata()
            target_path = download.get_wallpaper_path(date(2026, 7, 8), root_dir)
            target_path.parent.mkdir(parents=True)
            content = b"existing wallpaper missing hash"
            target_path.write_bytes(content)
            download.save_hashes(download.get_hash_file(root_dir), {})

            def fail_downloader(_url):
                self.fail("Downloader should not be called when target file exists.")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = download.process_wallpaper(
                    metadata,
                    root_dir=root_dir,
                    downloader=fail_downloader,
                    today=date(2026, 7, 9),
                )

            hash_value = download.calculate_sha256(content)
            hashes = download.load_hashes(download.get_hash_file(root_dir))
            self.assertEqual(result, download.STATUS_BACKFILLED)
            self.assertIn(hash_value, hashes)
            self.assertEqual(hashes[hash_value]["path"], "wallpapers/2026/07/20260708.jpg")
            self.assertIn("hash record was missing; backfilled hash", output.getvalue())

    def test_duplicate_hash_does_not_save_duplicate_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            metadata = self._metadata()
            content = b"duplicate wallpaper"
            hash_value = download.calculate_sha256(content)
            download.save_hashes(
                download.get_hash_file(root_dir),
                {
                    hash_value: {
                        "date": "2026-07-07",
                        "path": "wallpapers/2026/07/20260707.jpg",
                        "url": "https://www.bing.com/th?id=OHR.Other_1920x1080.jpg",
                    }
                },
            )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = download.process_wallpaper(
                    metadata,
                    root_dir=root_dir,
                    downloader=lambda _url: content,
                    today=date(2026, 7, 9),
                )

            target_path = download.get_wallpaper_path(date(2026, 7, 8), root_dir)
            hashes = download.load_hashes(download.get_hash_file(root_dir))
            self.assertEqual(result, download.STATUS_DUPLICATE)
            self.assertFalse(target_path.exists())
            self.assertEqual(list(hashes.keys()), [hash_value])
            self.assertIn("Duplicate image hash found, skipping", output.getvalue())

    def _metadata(self):
        return {
            "startdate": "20260708",
            "url": "/th?id=OHR.Example_1920x1080.jpg&pid=hp",
        }


if __name__ == "__main__":
    unittest.main()
