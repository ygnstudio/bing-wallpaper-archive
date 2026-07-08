import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "scripts" / "generate_index.py"
SPEC = importlib.util.spec_from_file_location("generate_index_script", SCRIPT_PATH)
generate_index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_index)


class GenerateIndexScriptTest(unittest.TestCase):
    def test_parse_date_from_filename_accepts_strict_standard_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            image_path = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"

            parsed_date = generate_index.parse_date_from_filename(image_path, root_dir)

            self.assertEqual(parsed_date, date(2026, 7, 8))

    def test_parse_date_from_filename_rejects_invalid_or_inconsistent_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            invalid_paths = [
                root_dir / "wallpapers" / "misc" / "20260708.jpg",
                root_dir / "wallpapers" / "2026" / "7" / "20260708.jpg",
                root_dir / "wallpapers" / "2025" / "07" / "20260708.jpg",
                root_dir / "wallpapers" / "2026" / "08" / "20260708.jpg",
                root_dir / "wallpapers" / "2026" / "02" / "20260231.jpg",
                root_dir / "wallpapers" / "2026" / "07" / "not-a-date.jpg",
                root_dir / "wallpapers" / "2026" / "07" / "20260708.jpeg",
            ]

            for image_path in invalid_paths:
                with self.subTest(image_path=image_path):
                    self.assertIsNone(
                        generate_index.parse_date_from_filename(image_path, root_dir)
                    )

    def test_get_thumbnail_path_maps_to_matching_thumbnail_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            image_path = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"

            thumbnail_path = generate_index.get_thumbnail_path(image_path, root_dir)

            self.assertEqual(
                thumbnail_path,
                root_dir / "thumbnails" / "2026" / "07" / "20260708.jpg",
            )

    def test_find_wallpaper_images_filters_invalid_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            valid_old = root_dir / "wallpapers" / "2026" / "07" / "20260707.jpg"
            valid_new = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"
            invalid_paths = [
                root_dir / "wallpapers" / "2026" / "07" / ".DS_Store",
                root_dir / "wallpapers" / "2026" / "07" / "20260709.png",
                root_dir / "wallpapers" / "misc" / "20260710.jpg",
                root_dir / "wallpapers" / "2026" / "08" / "20260711.jpg",
                root_dir / "wallpapers" / "2026" / "02" / "20260231.jpg",
            ]
            for path in [valid_old, valid_new, *invalid_paths]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"image")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                images = generate_index.find_wallpaper_images(root_dir)

            self.assertEqual(images, [valid_old, valid_new])
            self.assertIn(
                "Skipping invalid wallpaper path: wallpapers/misc/20260710.jpg",
                output.getvalue(),
            )
            self.assertIn(
                "Skipping invalid wallpaper path: wallpapers/2026/08/20260711.jpg",
                output.getvalue(),
            )
            self.assertIn(
                "Skipping invalid wallpaper path: wallpapers/2026/02/20260231.jpg",
                output.getvalue(),
            )

    def test_build_index_record_has_complete_relative_posix_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            image_path = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"image")
            metadata = {
                "2026-07-08": {
                    "title": "Bing title",
                    "copyright": "Original copyright",
                    "url": "https://www.bing.com/ignored.jpg",
                    "copyrightlink": "https://www.bing.com/ignored",
                }
            }

            record = generate_index.build_index_record(image_path, root_dir, metadata)

            self.assertEqual(
                record,
                {
                    "date": "2026-07-08",
                    "title": "Bing title",
                    "copyright": "Original copyright",
                    "image": "wallpapers/2026/07/20260708.jpg",
                    "thumbnail": "thumbnails/2026/07/20260708.jpg",
                },
            )
            self.assertEqual(set(record), {"date", "title", "copyright", "image", "thumbnail"})
            self.assertNotIn("\\", record["image"])
            self.assertNotIn("\\", record["thumbnail"])

    def test_build_index_record_uses_empty_strings_when_metadata_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            image_path = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"image")

            record = generate_index.build_index_record(image_path, root_dir, {})

            self.assertEqual(record["title"], "")
            self.assertEqual(record["copyright"], "")

    def test_build_index_records_sorts_desc_and_warns_for_missing_thumbnail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            old_image = root_dir / "wallpapers" / "2026" / "07" / "20260707.jpg"
            new_image = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"
            old_thumb = root_dir / "thumbnails" / "2026" / "07" / "20260707.jpg"
            for path in [old_image, new_image, old_thumb]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"image")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                records = generate_index.build_index_records(root_dir)

            self.assertEqual(
                [record["date"] for record in records],
                ["2026-07-08", "2026-07-07"],
            )
            self.assertIn(
                "Warning: thumbnail not found for wallpapers/2026/07/20260708.jpg",
                output.getvalue(),
            )

    def test_metadata_json_load_handles_missing_empty_invalid_and_object(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            metadata_path = root_dir / "data" / "metadata.json"

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(generate_index.load_metadata(root_dir), {})
            self.assertIn("Warning: data/metadata.json not found", output.getvalue())

            metadata_path.parent.mkdir(parents=True)
            metadata_path.write_text("", encoding="utf-8")
            self.assertEqual(generate_index.load_metadata(root_dir), {})

            metadata = {"2026-07-08": {"title": "Title", "copyright": "Copyright"}}
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            self.assertEqual(generate_index.load_metadata(root_dir), metadata)

            metadata_path.write_text("{broken json", encoding="utf-8")
            with self.assertRaises(ValueError):
                generate_index.load_metadata(root_dir)

    def test_write_index_uses_utf8_indent_no_ascii_escape_and_final_newline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            records = [
                {
                    "date": "2026-07-08",
                    "title": "湖",
                    "copyright": "",
                    "image": "wallpapers/2026/07/20260708.jpg",
                    "thumbnail": "thumbnails/2026/07/20260708.jpg",
                }
            ]

            generate_index.write_index(records, root_dir)

            index_path = root_dir / "data" / "index.json"
            content = index_path.read_text(encoding="utf-8")
            self.assertTrue(content.endswith("\n"))
            self.assertIn('  "title": "湖"', content)
            self.assertNotIn("\\u6e56", content)
            self.assertEqual(json.loads(content), records)

    def test_generate_index_writes_empty_array_when_no_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                records = generate_index.generate_index(root_dir)

            self.assertEqual(records, [])
            self.assertEqual(
                (root_dir / "data" / "index.json").read_text(encoding="utf-8"),
                "[]\n",
            )
            self.assertIn("No wallpaper images found.", output.getvalue())
            self.assertIn("Wrote empty index file: data/index.json", output.getvalue())


if __name__ == "__main__":
    unittest.main()
