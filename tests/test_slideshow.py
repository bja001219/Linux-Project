import tempfile
import unittest
from pathlib import Path

from PIL import Image

from slideshow import clean_folder, list_images, resize_images


class SlideshowTest(unittest.TestCase):
    def test_list_images_filters_and_sorts_supported_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("b.JPG", "a.png", "ignore.txt"):
                (root / name).write_bytes(b"x")

            self.assertEqual(
                [path.name for path in list_images(root)],
                ["a.png", "b.JPG"],
            )

    def test_resize_preserves_canvas_size_and_clears_stale_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            output.mkdir()
            Image.new("RGB", (400, 200), (255, 0, 0)).save(source / "wide.png")
            (output / "stale.txt").write_text("old", encoding="utf-8")

            resized = resize_images(
                source,
                output,
                (128, 72),
                background=(255, 255, 255),
            )

            self.assertEqual([path.name for path in resized], ["wide.png"])
            self.assertFalse((output / "stale.txt").exists())
            with Image.open(resized[0]) as result:
                self.assertEqual(result.size, (128, 72))

    def test_clean_folder_ignores_missing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            clean_folder(Path(directory) / "missing")


if __name__ == "__main__":
    unittest.main()
