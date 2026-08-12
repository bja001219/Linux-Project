"""Validation helpers kept separate from the Flask process for unit testing."""

from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
ALLOWED_FORMATS = {"PNG", "JPEG", "GIF"}


def sanitize_image_filename(filename: str) -> str | None:
    """Return a safe image filename, or ``None`` for unsupported input."""
    safe_name = secure_filename(filename)
    if not safe_name or "." not in safe_name:
        return None
    extension = safe_name.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return None
    return safe_name


def validate_image_upload(uploaded: FileStorage) -> str | None:
    """Validate both the normalized name and the actual image payload."""
    safe_name = sanitize_image_filename(uploaded.filename or "")
    if safe_name is None:
        return None

    try:
        with Image.open(uploaded.stream) as image:
            if image.format not in ALLOWED_FORMATS:
                return None
            image.verify()
    except (OSError, UnidentifiedImageError):
        return None
    finally:
        uploaded.stream.seek(0)
    return safe_name
