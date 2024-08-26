from flask import Flask, request, redirect, jsonify
import os
import time
import subprocess
import multiprocessing
from moviepy.editor import ImageSequenceClip
from PIL import Image

# Flask web server setup
app = Flask(__name__)
UPLOAD_FOLDER = 'uploaded_images'
RESIZED_FOLDER = 'resized_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return '''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload Images</title>
        <style>
            body {
                display: flex;
                justify-content: flex-start;
                align-items: flex-start;
                height: 100vh;
                background-color: #f0f0f0;
                margin: 0;
            }
            .container {
                background-color: white;
                width: 1000px;
                height: 800px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                border-radius: 10px;
                overflow: hidden;
                margin: 20px;
                padding: 20px;
                box-sizing: border-box;
            }
            header {
                background-color: skyblue;
                color: white;
                text-align: center;
                padding: 20px;
                font-size: 1.5em;
            }
            .content {
                padding: 20px;
                overflow-y: auto;
                height: calc(100% - 140px); /* Adjust based on header and form heights */
            }
            .image-list {
                list-style-type: none;
                padding: 0;
                margin: 0;
            }
            .image-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 5px 0;
            }
            .image-item img {
                max-width: 100px;
                max-height: 100px;
                margin-right: 10px;
            }
            .image-item button {
                background-color: red;
                color: white;
                border: none;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                cursor: pointer;
            }
            .dropzone {
                width: 100%;
                height: 100px;
                border: 2px dashed #cccccc;
                border-radius: 10px;
                display: flex;
                justify-content: center;
                align-items: center;
                color: #cccccc;
                margin-top: 10px;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                Upload Images
            </header>
            <div class="content">
                <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
                    <input id="fileInput" type="file" name="file" multiple style="display: none;">
                    <div class="dropzone" id="dropzone">Drag and drop images here or click to upload</div>
                    <ul class="image-list" id="imageList"></ul>
                    <input type="submit" value="Upload" style="margin-top: 10px;">
                </form>
            </div>
        </div>
        <script>
            document.getElementById('dropzone').addEventListener('click', function() {
                document.getElementById('fileInput').click();
            });

            document.getElementById('fileInput').addEventListener('change', function(event) {
                handleFiles(event.target.files);
            });

            document.getElementById('dropzone').addEventListener('dragover', function(event) {
                event.preventDefault();
            });

            document.getElementById('dropzone').addEventListener('drop', function(event) {
                event.preventDefault();
                handleFiles(event.dataTransfer.files);
            });

            function handleFiles(files) {
                const imageList = document.getElementById('imageList');
                for (let i = 0; i < files.length; i++) {
                    if (imageList.childElementCount >= 20) {
                        alert('You can upload up to 20 images only.');
                        break;
                    }
                    const li = document.createElement('li');
                    li.className = 'image-item';

                    const img = document.createElement('img');
                    img.src = URL.createObjectURL(files[i]);
                    img.onload = function() {
                        URL.revokeObjectURL(img.src);
                    };

                    li.appendChild(img);
                    li.appendChild(document.createTextNode(files[i].name));

                    const button = document.createElement('button');
                    button.textContent = 'x';
                    button.addEventListener('click', function() {
                        li.remove();
                    });
                    li.appendChild(button);
                    imageList.appendChild(li);
                }
            }
        </script>
    </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    files = request.files.getlist('file')
    if len(files) > 20:
        return 'You can upload up to 20 images only.'
    
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    with open('upload_complete.txt', 'w') as f:
        f.write('Upload complete')
    
    return 'Files uploaded successfully!'

def start_server():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='0.0.0.0', port=5000)

def resize_images(image_folder, output_folder, size=(1280, 720)):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    images = [img for img in os.listdir(image_folder) if img.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    for img_name in images:
        img_path = os.path.join(image_folder, img_name)
        with Image.open(img_path) as img:
            img.thumbnail(size, Image.ANTIALIAS)
            background = Image.new('RGB', size, (0, 0, 0))
            img_position = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
            background.paste(img, img_position)
            background.save(os.path.join(output_folder, img_name))

def create_video_from_images(image_folder, output_file):
    resize_images(image_folder, RESIZED_FOLDER)

    images = [os.path.join(RESIZED_FOLDER, img) for img in sorted(os.listdir(RESIZED_FOLDER)) if img.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    if len(images) == 0:
        raise ValueError("No images found in the specified folder.")
    
    durations = [60] * len(images)
    fps = 1 

    clip = ImageSequenceClip(images, durations=durations)
    clip.write_videofile(output_file, codec='libx264', fps=fps)

    clean_folder(RESIZED_FOLDER)

def clean_folder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)

def hide_taskbar():
    subprocess.run(['lxpanelctl', 'stop'])

def show_taskbar():
    subprocess.run(['lxpanelctl', 'restart'])

def play_video(video_file, video_process):
    if video_process and video_process.poll() is None:
        video_process.terminate()
    
    hide_taskbar()
    
    new_process = subprocess.Popen(['mpv', '--loop', '--fs', video_file])
    
    return new_process

def monitor_upload_status():
    video_process = None
    while True:
        if os.path.exists('upload_complete.txt'):
            create_video_from_images(UPLOAD_FOLDER, 'output_video.mp4')
            if video_process is not None:
                video_process.terminate()
            video_process = play_video('output_video.mp4', video_process)
            os.remove('upload_complete.txt')
            
            clean_folder(UPLOAD_FOLDER)

if __name__ == '__main__':
    server_process = multiprocessing.Process(target=start_server)
    server_process.start()
    time.sleep(5)

    monitor_upload_status()

    server_process.terminate()
