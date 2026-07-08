from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


ROOT_DIR = Path(__file__).resolve().parents[1]
WALLPAPERS_DIR = ROOT_DIR / "wallpapers"
THUMBNAILS_DIR = ROOT_DIR / "thumbnails"
MAX_THUMBNAIL_WIDTH = 480
SUPPORTED_SUFFIXES = {".jpg", ".jpeg"}

STATUS_GENERATED = "generated"
STATUS_SKIPPED = "skipped"


def find_wallpaper_images(root_dir=ROOT_DIR):
    """Find supported wallpaper images under wallpapers/."""
    wallpapers_dir = Path(root_dir) / "wallpapers"
    if not wallpapers_dir.exists():
        return []

    return sorted(
        path
        for path in wallpapers_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def get_thumbnail_path(image_path, root_dir=ROOT_DIR):
    """Map wallpapers/YYYY/MM/name.jpg to thumbnails/YYYY/MM/name.jpg."""
    root_path = Path(root_dir)
    image_path = Path(image_path)
    relative_path = image_path.relative_to(root_path / "wallpapers")
    return (root_path / "thumbnails" / relative_path).with_suffix(".jpg")


def generate_thumbnail(image_path, thumbnail_path):
    """Generate one JPEG thumbnail without overwriting existing files."""
    image_path = Path(image_path)
    thumbnail_path = Path(thumbnail_path)
    if thumbnail_path.exists():
        return STATUS_SKIPPED

    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as source_image:
        image = ImageOps.exif_transpose(source_image)
        image = image.convert("RGB")
        resized_image = resize_for_thumbnail(image)
        resized_image.save(
            thumbnail_path,
            format="JPEG",
            quality=85,
            optimize=True,
        )

    return STATUS_GENERATED


def resize_for_thumbnail(image):
    """Resize an image to max 480px width while preserving aspect ratio."""
    width, height = image.size
    if width <= MAX_THUMBNAIL_WIDTH:
        return image.copy()

    thumbnail_height = max(1, round(height * MAX_THUMBNAIL_WIDTH / width))
    resampling_filter = getattr(Image, "Resampling", Image).LANCZOS
    return image.resize((MAX_THUMBNAIL_WIDTH, thumbnail_height), resampling_filter)


def generate_all_thumbnails(root_dir=ROOT_DIR):
    """Generate thumbnails for every supported wallpaper image."""
    root_path = Path(root_dir)
    print("Scanning wallpapers directory...")
    image_paths = find_wallpaper_images(root_path)
    if not image_paths:
        print("No wallpaper images found.")
        return {"generated": 0, "skipped": 0}

    counts = {"generated": 0, "skipped": 0}
    for image_path in image_paths:
        thumbnail_path = get_thumbnail_path(image_path, root_path)
        result = generate_thumbnail(image_path, thumbnail_path)
        counts[result] += 1

        thumbnail_display_path = relative_path(thumbnail_path, root_path)
        if result == STATUS_GENERATED:
            print(f"Generated thumbnail: {thumbnail_display_path}")
        else:
            print(f"Thumbnail already exists, skipping: {thumbnail_display_path}")

    return counts


def relative_path(path, root_dir=ROOT_DIR):
    """Return a POSIX path relative to the repository root."""
    return Path(path).relative_to(Path(root_dir)).as_posix()


def main():
    """Entry point for generating thumbnails."""
    generate_all_thumbnails()


if __name__ == "__main__":
    main()
