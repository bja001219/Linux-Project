import unittest
from io import BytesIO

from PIL import Image
from werkzeug.datastructures import FileStorage

from upload_utils import sanitize_image_filename, validate_image_upload


class UploadUtilsTest(unittest.TestCase):
    def test_accepts_supported_extension_case_insensitively(self):
        self.assertEqual(sanitize_image_filename("Photo.JPEG"), "Photo.JPEG")

    def test_removes_path_traversal_segments(self):
        self.assertEqual(
            sanitize_image_filename("../../outside.png"),
            "outside.png",
        )

    def test_rejects_unsupported_or_empty_name(self):
        self.assertIsNone(sanitize_image_filename("payload.py"))
        self.assertIsNone(sanitize_image_filename(""))

    def test_accepts_a_real_image_payload(self):
        payload = BytesIO()
        Image.new("RGB", (2, 2), (255, 0, 0)).save(payload, format="PNG")
        payload.seek(0)

        uploaded = FileStorage(stream=payload, filename="safe.png")

        self.assertEqual(validate_image_upload(uploaded), "safe.png")
        self.assertEqual(uploaded.stream.tell(), 0)

    def test_rejects_non_image_content_with_image_extension(self):
        uploaded = FileStorage(
            stream=BytesIO(b"not an image"),
            filename="fake.png",
        )

        self.assertIsNone(validate_image_upload(uploaded))
        self.assertEqual(uploaded.stream.tell(), 0)


if __name__ == "__main__":
    unittest.main()
