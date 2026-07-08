import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "scripts" / "generate_thumbnail.py"
SPEC = importlib.util.spec_from_file_location("generate_thumbnail_script", SCRIPT_PATH)
thumbnail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(thumbnail)


class GenerateThumbnailScriptTest(unittest.TestCase):
    def test_get_thumbnail_path_preserves_date_dirs_and_outputs_jpg(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            image_path = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpeg"

            thumbnail_path = thumbnail.get_thumbnail_path(image_path, root_dir)

            self.assertEqual(
                thumbnail_path,
                root_dir / "thumbnails" / "2026" / "07" / "20260708.jpg",
            )

    def test_find_wallpaper_images_returns_jpg_and_jpeg_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            wallpaper_dir = root_dir / "wallpapers" / "2026" / "07"
            wallpaper_dir.mkdir(parents=True)
            expected_jpg = wallpaper_dir / "20260708.jpg"
            expected_jpeg = wallpaper_dir / "20260709.jpeg"
            expected_jpg.write_bytes(b"jpg")
            expected_jpeg.write_bytes(b"jpeg")
            (wallpaper_dir / "not-image.png").write_bytes(b"png")
            (wallpaper_dir / "notes.txt").write_text("notes", encoding="utf-8")

            images = thumbnail.find_wallpaper_images(root_dir)

            self.assertEqual(images, [expected_jpg, expected_jpeg])

    def test_generate_thumbnail_creates_directory_and_480px_jpeg(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            image_path = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"
            thumbnail_path = root_dir / "thumbnails" / "2026" / "07" / "20260708.jpg"
            self._create_image(image_path, size=(1920, 1080))

            result = thumbnail.generate_thumbnail(image_path, thumbnail_path)

            self.assertEqual(result, thumbnail.STATUS_GENERATED)
            with Image.open(thumbnail_path) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.size, (480, 270))

    def test_generate_thumbnail_resaves_small_image_without_upscaling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            image_path = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"
            thumbnail_path = root_dir / "thumbnails" / "2026" / "07" / "20260708.jpg"
            self._create_image(image_path, size=(320, 180))

            result = thumbnail.generate_thumbnail(image_path, thumbnail_path)

            self.assertEqual(result, thumbnail.STATUS_GENERATED)
            self.assertNotEqual(image_path.read_bytes(), thumbnail_path.read_bytes())
            with Image.open(thumbnail_path) as image:
                self.assertEqual(image.size, (320, 180))
                self.assertEqual(image.format, "JPEG")

    def test_generate_thumbnail_skips_existing_file_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            image_path = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"
            thumbnail_path = root_dir / "thumbnails" / "2026" / "07" / "20260708.jpg"
            self._create_image(image_path, size=(1920, 1080))
            thumbnail_path.parent.mkdir(parents=True)
            thumbnail_path.write_bytes(b"existing thumbnail")

            result = thumbnail.generate_thumbnail(image_path, thumbnail_path)

            self.assertEqual(result, thumbnail.STATUS_SKIPPED)
            self.assertEqual(thumbnail_path.read_bytes(), b"existing thumbnail")

    def test_generate_all_thumbnails_reports_no_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                result = thumbnail.generate_all_thumbnails(Path(temp_dir))

            self.assertEqual(result, {"generated": 0, "skipped": 0})
            self.assertIn("No wallpaper images found.", output.getvalue())

    def test_generate_all_thumbnails_generates_then_skips(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            image_path = root_dir / "wallpapers" / "2026" / "07" / "20260708.jpg"
            self._create_image(image_path, size=(1920, 1080))

            first_output = io.StringIO()
            with contextlib.redirect_stdout(first_output):
                first_result = thumbnail.generate_all_thumbnails(root_dir)

            second_output = io.StringIO()
            with contextlib.redirect_stdout(second_output):
                second_result = thumbnail.generate_all_thumbnails(root_dir)

            self.assertEqual(first_result, {"generated": 1, "skipped": 0})
            self.assertEqual(second_result, {"generated": 0, "skipped": 1})
            self.assertIn(
                "Generated thumbnail: thumbnails/2026/07/20260708.jpg",
                first_output.getvalue(),
            )
            self.assertIn(
                "Thumbnail already exists, skipping: thumbnails/2026/07/20260708.jpg",
                second_output.getvalue(),
            )

    def _create_image(self, path, size):
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", size, color=(64, 128, 192))
        image.save(path, format="JPEG", quality=95)


if __name__ == "__main__":
    unittest.main()
