import os
import time
import subprocess
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pytz
from moviepy.editor import ImageSequenceClip
from PIL import Image, ImageOps

SERVICE_ACCOUNT_FILE = 'service_account_key.json'

SCOPES = ['https://www.googleapis.com/auth/drive']

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

FOLDER_ID = '1S44Iww0VWqhJTwgYC0aXU9BMyRGATHMK'
DOWNLOAD_FOLDER = 'images' 
RESIZED_FOLDER = 'resized_images' 
CHECK_INTERVAL = 60 
VIDEO_FILE = 'slideshow.mp4'
IMAGE_DISPLAY_DURATION = 60 
VIDEO_SIZE = (1280, 720)  


def download_file(file_id, destination):
    request = drive_service.files().get_media(fileId=file_id)
    with open(destination, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f'Download {int(status.progress() * 100)}%.')

def get_unix_timestamp(iso_time_str):

    utc_time = datetime.strptime(iso_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    return int(utc_time.timestamp())

def download_images():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    query = f"'{FOLDER_ID}' in parents and mimeType contains 'image/'"
    results = drive_service.files().list(q=query, fields="files(id, name, modifiedTime)").execute()
    files = results.get('files', [])

    current_image_count = len(files)
    image_updated = False

    for file in files:
        file_id = file['id']
        file_name = file['name']
        file_path = os.path.join(DOWNLOAD_FOLDER, file_name)

        remote_modified_time = get_unix_timestamp(file['modifiedTime'])
        if os.path.exists(file_path):
            local_modified_time = int(os.path.getmtime(file_path))
            local_modified_time = datetime.fromtimestamp(local_modified_time, tz=pytz.UTC).timestamp()
        else:
            local_modified_time = 0

        if remote_modified_time > local_modified_time:
            print(f'Downloading new or updated file: {file_name}')
            download_file(file_id, file_path)
            image_updated = True
        else:
            print(f'File {file_name} is up-to-date.')

    downloaded_files = set(os.listdir(DOWNLOAD_FOLDER))
    drive_files = {file['name'] for file in files}
    deleted_files = downloaded_files - drive_files

    if deleted_files:
        image_updated = True
        for file_name in deleted_files:
            os.remove(os.path.join(DOWNLOAD_FOLDER, file_name))
            print(f'Deleted file: {file_name}')

    return image_updated, current_image_count

def resize_images(image_folder, output_folder, size):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    else:
        for file in os.listdir(output_folder):
            file_path = os.path.join(output_folder, file)
            if os.path.isfile(file_path):
                os.remove(file_path)

    for img_name in os.listdir(image_folder):
        if img_name.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            img_path = os.path.join(image_folder, img_name)
            output_path = os.path.join(output_folder, img_name)
            with Image.open(img_path) as img:
                img = img.convert('RGB')
                img.thumbnail(size, Image.ANTIALIAS)
                img_resized = Image.new("RGB", size, (255, 255, 255))
                img_resized.paste(
                    img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
                )
                img_resized.save(output_path)

def create_video_from_images(image_folder, output_file):
    resize_images(image_folder, RESIZED_FOLDER, VIDEO_SIZE)

    images = [os.path.join(RESIZED_FOLDER, img) for img in sorted(os.listdir(RESIZED_FOLDER)) if img.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    if len(images) == 0:
        raise ValueError("No images found in the specified folder.")
    
    durations = [IMAGE_DISPLAY_DURATION] * len(images) 
    fps = 1  

    clip = ImageSequenceClip(images, durations=durations)
    clip.write_videofile(output_file, codec='libx264', fps=fps)

def show_default_image():
    default_img_path = os.path.join(DEFAULT_IMAGE_PATH, DEFAULT_IMAGE)
    img = Image.open(default_img_path)
    img.thumbnail(VIDEO_SIZE, Image.ANTIALIAS)
    img_resized = Image.new("RGB", VIDEO_SIZE, (255, 255, 255))
    img_resized.paste(img, ((VIDEO_SIZE[0] - img.width) // 2, (VIDEO_SIZE[1] - img.height) // 2))
    img_resized.save('default_display.jpg')
    
    subprocess.run(['mpv', '--fs', 'default_display.jpg'])

def play_video(video_file, video_process):
    if video_process and video_process.poll() is None:
        video_process.terminate()
    
    new_process = subprocess.Popen(['mpv', '--loop', '--fs', video_file])
    
    return new_process

def main():
    video_process = None
    current_image_count = 0

    while True:
        try:
            image_updated, new_image_count = download_images()

            if image_updated or new_image_count != current_image_count:
                if os.path.exists(VIDEO_FILE):
                    os.remove(VIDEO_FILE)
                
                if os.path.exists(RESIZED_FOLDER):
                    for file in os.listdir(RESIZED_FOLDER):
                        file_path = os.path.join(RESIZED_FOLDER, file)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                
                create_video_from_images(DOWNLOAD_FOLDER, VIDEO_FILE)
                video_process = play_video(VIDEO_FILE, video_process)
                current_image_count = new_image_count

        except Exception as e:
            print(f'An error occurred: {e}')
            show_default_image()

        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
