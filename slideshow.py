"""Shared image-to-video helpers for both execution modes."""

from pathlib import Path

from moviepy.editor import ImageSequenceClip
from PIL import Image

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}
RESAMPLE_FILTER = getattr(Image, "Resampling", Image).LANCZOS


def list_images(folder: str | Path) -> list[Path]:
    """Return supported image files in deterministic filename order."""
    root = Path(folder)
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def clean_folder(folder: str | Path) -> None:
    """Remove regular files from a known runtime working directory."""
    root = Path(folder)
    if not root.exists():
        return
    for path in root.iterdir():
        if path.is_file():
            path.unlink()


def resize_images(
    image_folder: str | Path,
    output_folder: str | Path,
    size: tuple[int, int],
    *,
    background: tuple[int, int, int] = (0, 0, 0),
) -> list[Path]:
    """Fit images into a fixed canvas while preserving aspect ratio."""
    output = Path(output_folder)
    output.mkdir(parents=True, exist_ok=True)
    clean_folder(output)

    resized: list[Path] = []
    for source in list_images(image_folder):
        destination = output / source.name
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail(size, RESAMPLE_FILTER)
            canvas = Image.new("RGB", size, background)
            position = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
            canvas.paste(image, position)
            canvas.save(destination)
        resized.append(destination)
    return resized


def create_video_from_images(
    image_folder: str | Path,
    resized_folder: str | Path,
    output_file: str | Path,
    *,
    size: tuple[int, int] = (1280, 720),
    display_duration: int = 60,
    fps: int = 1,
    background: tuple[int, int, int] = (0, 0, 0),
) -> None:
    """Create an H.264 slideshow from all supported images in a folder."""
    images = resize_images(
        image_folder,
        resized_folder,
        size,
        background=background,
    )
    if not images:
        raise ValueError("No images found in the specified folder.")

    clip = ImageSequenceClip(
        [str(path) for path in images],
        durations=[display_duration] * len(images),
    )
    try:
        clip.write_videofile(str(output_file), codec="libx264", fps=fps)
    finally:
        clip.close()
