import os
from PIL import Image

import time
import threading
import cwiid
import pyautogui

from flask import Flask, render_template_string
import os
from flask import send_from_directory
import webbrowser

PICS_FOLDER = 'pics'
THUMBS_FOLDER = 'thumbs'
PORT = 51103

#########################
# make thumbs directory #
#########################

def create_thumbnail(image_path, thumbnail_path):
    with Image.open(image_path) as img:
        img.thumbnail((200, 150))
        img.save(thumbnail_path)

def mirror_directory_with_thumbnails(src_dir, dst_dir):
    for root, dirs, files in os.walk(src_dir):
        rel_path = os.path.relpath(root, src_dir)
        dst_folder = os.path.join(dst_dir, rel_path)

        # Create corresponding directory in the destination
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)

        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dst_folder, file)

                # Only create thumbnail if it doesn't already exist
                if not os.path.exists(dst_file):
                    create_thumbnail(src_file, dst_file)

mirror_directory_with_thumbnails(PICS_FOLDER, THUMBS_FOLDER)

###########
# wiimote #
###########

filtered_x, filtered_y = 512, 384
raw_x, raw_y = 512, 384

def mouse_thread():
    global filtered_x, filtered_y
    alpha = 0.1

    while True:

        filtered_x = alpha*raw_x + (1-alpha) * filtered_x
        filtered_y = alpha*raw_y + (1-alpha) * filtered_y

        time.sleep(0.01)

threading.Thread(target = mouse_thread, daemon = True).start()

print("Press 1 + 2 on your Wii Remote to connect...")
wm = cwiid.Wiimote()

def wii_thread():
    global raw_x, raw_y

    wm.rpt_mode = cwiid.RPT_BTN | cwiid.RPT_IR

    last_buttons = 0
    last_action = time.time()

    while True:

        buttons = wm.state['buttons']

        if buttons & cwiid.BTN_LEFT and not last_buttons & cwiid.BTN_LEFT:
            if time.time() - last_action > 2:
                pyautogui.press('left')
                last_action = time.time()

        if buttons & cwiid.BTN_RIGHT and not last_buttons & cwiid.BTN_RIGHT:
            if time.time() - last_action > 2:
                pyautogui.press('right')
                last_action = time.time()

        if buttons & cwiid.BTN_A and not last_buttons & cwiid.BTN_A:
            if time.time() - last_action > 2:
                pyautogui.click()
                last_action = time.time()
                
        if buttons & cwiid.BTN_UP and not last_buttons & cwiid.BTN_UP:
            if time.time() - last_action > 1:
                pyautogui.press('pageup')
                last_action = time.time()

        if buttons & cwiid.BTN_DOWN and not last_buttons & cwiid.BTN_DOWN:
            if time.time() - last_action > 1:
                pyautogui.press('pagedown')
                last_action = time.time()

        if buttons & cwiid.BTN_HOME and not last_buttons & cwiid.BTN_HOME:
            pyautogui.press('backspace')

        last_buttons = buttons

        ir_data = wm.state['ir_src']
        valid_dots = [dot for dot in ir_data if dot]

        if valid_dots:
            raw_x, raw_y = valid_dots[0]['pos']

        time.sleep(0.01)

threading.Thread(target = wii_thread, daemon = True).start()

################
# start server #
################

app = Flask(__name__)

def scan_folder(folder):
    files = []
    for root, dirs, filenames in os.walk(folder):
        for filename in filenames:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.avi', '.mov', '.mkv')):
                files.append(os.path.join(root, filename))
    files = sorted(files)
    return files

@app.route('/')
def index():
    files = scan_folder(PICS_FOLDER)
    html_content = '''
    <!doctype html>
    <html>
    <head><title>DiaShow</title>
        <style>
        img {
            max-width: 100%;
            max-height: 100%;
            display: block;
            margin: auto;
        }
        span {
            display: inline-block;
            max-width: 160px;
            height: 120px;
            justify-content: center;
            align-items: center;
        }
        body{
            background-color: #aaaaaa;
            text-align:center;
        }
        #fullscreen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: #aaaaaa;
            display: none;
            justify-content: center;
            align-items: center;
        }
        #fullscreen img {
            width: 100%;
            height: 100%;
            object-fit:contain;
        }
    </style>
    
    <script>
        function openFullscreen(index) {
            currentIndex = index;
            document.getElementById('fullscreenImg').src = files[currentIndex];
            document.getElementById('fullscreen').style.display = 'flex';
        }

        function closeFullscreen() {
            document.getElementById('fullscreen').style.display = 'none';
        }
        
        let currentIndex = 0;
        const files = [
            {% for file in files %}
                "{{ file }}",
            {% endfor %}
        ];

        document.onkeydown = function(e) {
            if (document.getElementById('fullscreen').style.display === 'flex') {
                if (e.key === 'ArrowRight') {
                    currentIndex = (currentIndex + 1) % files.length;
                    document.getElementById('fullscreenImg').src = files[currentIndex];
                } else if (e.key === 'ArrowLeft') {
                    currentIndex = (currentIndex - 1 + files.length) % files.length;
                    document.getElementById('fullscreenImg').src = files[currentIndex];
                } else if (e.key === 'Backspace') {
                    closeFullscreen();
                    e.preventDefault();
                }
            }
        };
    </script>
    
    </head>
    <body>
        {% for file in files %}
            <span><img src="{{ file.replace('PICS_FOLDER', 'THUMBS_FOLDER', 1) }}" onclick="openFullscreen({{ loop.index0 }})"/></span>
        {% endfor %}
        
        <div id="fullscreen" onclick="document.onkeydown({key:'ArrowRight'})">
            <img id="fullscreenImg" src="" />
        </div>
    </body>
    </html>
    '''.replace('PICS_FOLDER', PICS_FOLDER).replace('THUMBS_FOLDER', THUMBS_FOLDER)
    return render_template_string(html_content, files = files)

@app.route('/<path:folder>/<filename>')
def serve_file(folder, filename):
    return send_from_directory(folder, filename)

webbrowser.open(f'http://localhost:{PORT}')
app.run(debug = False, port=51103)
