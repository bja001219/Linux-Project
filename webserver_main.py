"""Local-network image upload server and slideshow player."""

import multiprocessing
import os
import subprocess
import time
from pathlib import Path

from flask import Flask, redirect, request

from slideshow import clean_folder, create_video_from_images
from upload_utils import validate_image_upload

app = Flask(__name__)
UPLOAD_FOLDER = Path(os.getenv("SLIDESHOW_UPLOAD_FOLDER", "uploaded_images"))
RESIZED_FOLDER = Path(os.getenv("SLIDESHOW_RESIZED_FOLDER", "resized_images"))
VIDEO_FILE = Path(os.getenv("SLIDESHOW_VIDEO_FILE", "output_video.mp4"))
UPLOAD_MARKER = Path(os.getenv("SLIDESHOW_UPLOAD_MARKER", "upload_complete.txt"))
MAX_FILES = 20

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = int(
    os.getenv("SLIDESHOW_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))
)


@app.route("/")
def index():
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload Images</title>
        <style>
            body { display:flex; justify-content:center; background:#f0f0f0; margin:0; font-family:sans-serif; }
            .container { background:white; width:min(1000px, calc(100% - 40px)); min-height:500px;
                         box-shadow:0 4px 8px rgba(0,0,0,.2); border-radius:10px; margin:20px; padding:20px; }
            header { background:skyblue; color:white; text-align:center; padding:20px; font-size:1.5em; }
            .content { padding:20px; }
            .image-list { list-style:none; padding:0; }
            .image-item { display:flex; align-items:center; gap:10px; padding:5px 0; }
            .image-item img { max-width:100px; max-height:100px; }
            .dropzone { height:100px; border:2px dashed #aaa; border-radius:10px; display:flex;
                        justify-content:center; align-items:center; color:#777; margin-top:10px; cursor:pointer; }
        </style>
    </head>
    <body>
      <div class="container">
        <header>Upload Images</header>
        <div class="content">
          <form action="/upload" method="post" enctype="multipart/form-data">
            <input id="fileInput" type="file" name="file" accept="image/png,image/jpeg,image/gif"
                   multiple style="display:none">
            <div class="dropzone" id="dropzone">Drag and drop images here or click to upload</div>
            <ul class="image-list" id="imageList"></ul>
            <input type="submit" value="Upload">
          </form>
        </div>
      </div>
      <script>
        const input = document.getElementById('fileInput');
        const zone = document.getElementById('dropzone');
        const list = document.getElementById('imageList');
        zone.addEventListener('click', () => input.click());
        zone.addEventListener('dragover', event => event.preventDefault());
        zone.addEventListener('drop', event => {
          event.preventDefault();
          input.files = event.dataTransfer.files;
          renderFiles(input.files);
        });
        input.addEventListener('change', () => renderFiles(input.files));
        function renderFiles(files) {
          list.replaceChildren();
          Array.from(files).slice(0, 20).forEach(file => {
            const item = document.createElement('li');
            item.className = 'image-item';
            const image = document.createElement('img');
            image.src = URL.createObjectURL(file);
            image.onload = () => URL.revokeObjectURL(image.src);
            item.append(image, document.createTextNode(file.name));
            list.append(item);
          });
        }
      </script>
    </body>
    </html>
    """


@app.route("/upload", methods=["POST"])
def upload_file():
    files = request.files.getlist("file")
    if not files:
        return redirect(request.url)
    if len(files) > MAX_FILES:
        return f"You can upload up to {MAX_FILES} images only.", 400

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    saved = 0
    for uploaded in files:
        safe_name = validate_image_upload(uploaded)
        if safe_name is None:
            continue
        uploaded.save(UPLOAD_FOLDER / safe_name)
        saved += 1

    if saved == 0:
        return "No supported image files were uploaded.", 400

    UPLOAD_MARKER.write_text("Upload complete", encoding="utf-8")
    return f"{saved} image(s) uploaded successfully!"


def start_server() -> None:
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


def hide_taskbar() -> None:
    subprocess.run(["lxpanelctl", "stop"], check=False)


def show_taskbar() -> None:
    subprocess.run(["lxpanelctl", "restart"], check=False)


def play_video(video_file: Path, video_process: subprocess.Popen | None):
    if video_process and video_process.poll() is None:
        video_process.terminate()
        video_process.wait(timeout=5)
    hide_taskbar()
    return subprocess.Popen(["mpv", "--loop", "--fs", str(video_file)])


def monitor_upload_status() -> None:
    video_process = None
    try:
        while True:
            if UPLOAD_MARKER.exists():
                create_video_from_images(
                    UPLOAD_FOLDER,
                    RESIZED_FOLDER,
                    VIDEO_FILE,
                    background=(0, 0, 0),
                )
                video_process = play_video(VIDEO_FILE, video_process)
                UPLOAD_MARKER.unlink(missing_ok=True)
                clean_folder(UPLOAD_FOLDER)
            time.sleep(0.25)
    finally:
        if video_process and video_process.poll() is None:
            video_process.terminate()
        show_taskbar()


if __name__ == "__main__":
    server_process = multiprocessing.Process(target=start_server)
    server_process.start()
    try:
        monitor_upload_status()
    except KeyboardInterrupt:
        print("Stopping upload server.")
    finally:
        server_process.terminate()
        server_process.join(timeout=5)
