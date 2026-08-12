"""Poll Google Drive and play a regenerated slideshow on Raspberry Pi."""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from slideshow import create_video_from_images

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account_key.json")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

DOWNLOAD_FOLDER = Path(os.getenv("SLIDESHOW_DOWNLOAD_FOLDER", "images"))
RESIZED_FOLDER = Path(os.getenv("SLIDESHOW_RESIZED_FOLDER", "resized_images"))
VIDEO_FILE = Path(os.getenv("SLIDESHOW_VIDEO_FILE", "slideshow.mp4"))
DEFAULT_IMAGE_FILE = os.getenv("SLIDESHOW_DEFAULT_IMAGE", "")

CHECK_INTERVAL = int(os.getenv("SLIDESHOW_CHECK_INTERVAL", "60"))
IMAGE_DISPLAY_DURATION = int(os.getenv("SLIDESHOW_IMAGE_DURATION", "60"))
VIDEO_SIZE = (1280, 720)


def build_drive_service():
    """Create the Drive client at application startup, not import time."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=credentials)


def download_file(drive_service, file_id: str, destination: Path) -> None:
    request = drive_service.files().get_media(fileId=file_id)
    with destination.open("wb") as output:
        downloader = MediaIoBaseDownload(output, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status is not None:
                print(f"Download {int(status.progress() * 100)}%.")


def get_unix_timestamp(iso_time: str) -> int:
    """Parse Google Drive RFC3339 timestamps with or without fractions."""
    return int(datetime.fromisoformat(iso_time.replace("Z", "+00:00")).timestamp())


def download_images(drive_service) -> tuple[bool, int]:
    DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    query = f"'{FOLDER_ID}' in parents and mimeType contains 'image/' and trashed = false"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
    ).execute()
    files = results.get("files", [])
    image_updated = False

    for remote_file in files:
        # Drive filenames are external input. Keep only the basename before writing.
        file_name = Path(remote_file["name"]).name
        file_path = DOWNLOAD_FOLDER / file_name
        remote_modified = get_unix_timestamp(remote_file["modifiedTime"])
        local_modified = int(file_path.stat().st_mtime) if file_path.exists() else 0

        if remote_modified > local_modified:
            print(f"Downloading new or updated file: {file_name}")
            download_file(drive_service, remote_file["id"], file_path)
            image_updated = True
        else:
            print(f"File {file_name} is up-to-date.")

    downloaded_files = {path.name for path in DOWNLOAD_FOLDER.iterdir() if path.is_file()}
    drive_files = {Path(remote_file["name"]).name for remote_file in files}
    for file_name in downloaded_files - drive_files:
        (DOWNLOAD_FOLDER / file_name).unlink()
        image_updated = True
        print(f"Deleted file: {file_name}")

    return image_updated, len(files)


def show_default_image() -> None:
    """Display an optional fallback without masking the original failure."""
    if not DEFAULT_IMAGE_FILE:
        print("SLIDESHOW_DEFAULT_IMAGE is not configured; skipping fallback image.")
        return
    path = Path(DEFAULT_IMAGE_FILE)
    if not path.is_file():
        print(f"Fallback image does not exist: {path}")
        return
    subprocess.run(["mpv", "--fs", str(path)], check=False)


def play_video(video_file: Path, video_process: subprocess.Popen | None):
    if video_process and video_process.poll() is None:
        video_process.terminate()
        video_process.wait(timeout=5)
    return subprocess.Popen(["mpv", "--loop", "--fs", str(video_file)])


def main() -> None:
    if not FOLDER_ID:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID environment variable is required.")

    drive_service = build_drive_service()
    video_process = None
    current_image_count = 0
    try:
        while True:
            try:
                image_updated, new_image_count = download_images(drive_service)
                if image_updated or new_image_count != current_image_count:
                    create_video_from_images(
                        DOWNLOAD_FOLDER,
                        RESIZED_FOLDER,
                        VIDEO_FILE,
                        size=VIDEO_SIZE,
                        display_duration=IMAGE_DISPLAY_DURATION,
                        background=(255, 255, 255),
                    )
                    video_process = play_video(VIDEO_FILE, video_process)
                    current_image_count = new_image_count
            # This is the recovery boundary for one polling cycle: a transient
            # Drive, filesystem, encoding, or player failure must not stop signage.
            except Exception as error:  # noqa: BLE001
                print(f"An error occurred: {error}")
                show_default_image()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("Stopping slideshow monitor.")
    finally:
        if video_process and video_process.poll() is None:
            video_process.terminate()


if __name__ == "__main__":
    main()
