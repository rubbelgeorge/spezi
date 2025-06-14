import webbrowser
import requests
import subprocess
import re
import time
from datetime import datetime, timedelta
import threading
import objc
import json
import os
from Foundation import NSObject
from ScriptingBridge import SBApplication
from flask import Flask, render_template
from flask import send_file
from flask import jsonify, request
SETTINGS_FILE = "settings.json"

def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

settings = load_settings()

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)
from io import BytesIO
import base64
import hashlib
import subprocess

def floats_differ(a, b, epsilon=1e-3):
    return abs(a - b) > epsilon

app = Flask(__name__)
VERSION = "0.0.3"
import logging
werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.DEBUG)  # Enable GET logs

# To re-enable normal logging, just change the level back:
# werkzeug_log.setLevel(logging.INFO)

current_info = {"sample_rate": None, "status": "Waiting...", "artwork_version": 0}
nowplaying_info = {}
device_info = {}
artist_art_url = None

last_album_id = None
last_artwork = None
last_avc = None
last_hevc = None

def get_current_playback_info():
    music = SBApplication.applicationWithBundleIdentifier_("com.apple.Music")
    if not music or not music.isRunning():
        return None, None

    current_track = music.currentTrack()
    player_position = music.playerPosition()

    if current_track:
        duration = current_track.duration()
        return duration, player_position
    else:
        return None, None

# -- AppleScript to get current track info --
def get_track_info(which='current'):
    script = f'''
    tell application "Music"
        set t to {which} track
        return (get name of t) & "¶" & (get artist of t)
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    name, artist = result.stdout.strip().split("¶")
    return {"name": name, "artist": artist}

# -- Use log show to look for recent sample rate info --
def get_recent_sample_rate(seconds=5):
    now = datetime.now()
    start_time = now - timedelta(seconds=seconds)
    start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')

    cmd = [
        'log', 'show',
        '--predicate',
        '(process == "Music") && (eventMessage CONTAINS "asbdSampleRate")',
        '--style', 'syslog',
        '--start', start_str,
        '--info', '--debug', '--last', f'{seconds}s'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    logs = result.stdout

    # Look for lines like: "asbdSampleRate = 44100.0 kHz"
    match = re.search(r'asbdSampleRate\s*=\s*([\d.]+)', logs)
    if match:
        return float(match.group(1))
    return None

class MusicApp(NSObject):
    def init(self):
        self = objc.super(MusicApp, self).init()
        if self is None:
            return None
        self.music = SBApplication.applicationWithBundleIdentifier_("com.apple.Music")
        return self

    def pause(self):
        self.music.pause()

    def play(self):
        self.music.playOnce_(None)

def monitor_sample_rate():
    print("Monitoring sample rate logs... Press Ctrl+C to stop.")

    process = subprocess.Popen(
        ['log', 'stream',
         '--predicate', '(process == "Music") AND (eventMessage CONTAINS "SampleRate" OR eventMessage CONTAINS "asbdSampleRate")',
         '--style', 'syslog', '--info', '--debug'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        text=True
    )

    prev_sample_rate = None
    next_sample_rate = None

    music_app = MusicApp.alloc().init()

    try:
        for line in process.stdout:
            #print(f"line:{line}")
            # Determine if this is a "current" or "next" sample rate based on the log line source
            if "FigStreamPlayer" in line and "SampleRate" in line:
                rendition_match = re.search(r'\[Rendition ([^\]]+)\]', line)
                bitdepth_match = re.search(r'\[BitDepth (\d+)\]', line)
                rendition = rendition_match.group(1) if rendition_match else "Unknown"
                bitdepth = int(bitdepth_match.group(1)) if bitdepth_match else None
                current_info["rendition"] = rendition
                current_info["bitdepth"] = bitdepth

                match = re.search(r'\[SampleRate\s+(\d+(?:\.\d+)?)\]', line)
                if match:
                    sample_rate = float(match.group(1))
                    if prev_sample_rate is not None:
                        if floats_differ(sample_rate, prev_sample_rate):
                            print(f"Sample rate changed: {prev_sample_rate} kHz -> {sample_rate} kHz")
                        else:
                            print(f"Sample rate unchanged: still {sample_rate} kHz")
                    if prev_sample_rate is None or floats_differ(sample_rate, prev_sample_rate):
                        match_time = datetime.now()
                        print(f"Current sample rate: {sample_rate} kHz")
                        pause_start = datetime.now()
                        music_app.pause()
                        pause_end = datetime.now()
                        pause_duration = (pause_end - pause_start).total_seconds()
                        #print(f"Pause script duration: {pause_duration:.2f}s")
                        pause_time = datetime.now()
                        elapsed = (pause_time - match_time).total_seconds()
                        #print(f"Paused at {pause_time.strftime('%H:%M:%S')} (elapsed {elapsed:.2f}s since detection)")
                        print(f"Paused")
                        # Load sample rate matching from settings
                        sample_rate_match = settings.get("sample_rate_match", {})
                        enabled = sample_rate_match.get("enabled", False)
                        mappings = sample_rate_match.get("mapping", {})

                        target_sample_rate = sample_rate  # Default: no remapping

                        if enabled:
                            # Normalize sample rate to kHz for mapping lookup
                            normalized_sample_rate_khz = int(sample_rate / 1000)
                            mapped_value = mappings.get(str(normalized_sample_rate_khz))
                            if mapped_value is not None:
                                target_sample_rate = mapped_value * 1000  # convert back to Hz
                                print(f"✅ Sample rate matching applied: {normalized_sample_rate_khz} kHz -> {mapped_value} kHz")
                            else:
                                print(f"⚠️ No mapping for {normalized_sample_rate_khz} kHz found in user settings. Using original sample rate.")
                        else:
                            print("ℹ️ Sample rate matching disabled.")

                        subprocess.run(['./srswitch.swift', str(target_sample_rate)])

                        music_app.play()
                        print(f"Resumed")
                        prev_sample_rate = sample_rate
                        next_sample_rate = None  # Reset any pending "next" value

                        current_info["sample_rate"] = sample_rate
                        current_info["status"] = f"Paused and resumed at {datetime.now().strftime('%H:%M:%S')} with sample rate {sample_rate} kHz"

            elif "mediaFormatinfo" in line and "asbdSampleRate" in line:
                match = re.search(r'asbdSampleRate\s*=\s*([\d.]+)', line)
                if match:
                    sample_rate = float(match.group(1))
                    if sample_rate != prev_sample_rate and sample_rate != next_sample_rate:
                        next_sample_rate = sample_rate
                        #print(f"Next sample rate: {sample_rate} kHz")
    except KeyboardInterrupt:
        process.terminate()
        print("\nStopped monitoring.")

def monitor_now_playing():
    global last_album_id, last_artwork, last_avc, last_hevc
    subprocess.Popen(['swift', 'nowplaying.swift'])
    while True:
        try:
            with open("nowplaying.json", "r") as f:
                data = json.load(f)
                nowplaying_info.clear()
                nowplaying_info.update(data)
                album_id = data.get("Album ID")
                if album_id or "iTunes Track ID" in data:
                    if album_id:
                        lookup_id = album_id
                        lookup_type = "album-id"
                    else:
                        lookup_id = data["iTunes Track ID"]
                        lookup_type = "track-id"
                        if lookup_id != last_album_id:
                            print(f"No album ID found. Using track ID {lookup_id} as fallback.")
                    if lookup_id != last_album_id:
                        def fetch_artwork(lookup_id):
                            result = subprocess.run(
                                ['python', 'artwork.py', f'--{lookup_type}', str(lookup_id)],
                                capture_output=True, text=True
                            )
                            avc = hevc = artwork = None
                            for line in result.stdout.splitlines():
                                if line.startswith("AVC:"):
                                    avc = line.split(":", 1)[1].strip()
                                elif line.startswith("HEVC:"):
                                    hevc = line.split(":", 1)[1].strip()
                                elif line.startswith("Artwork:"):
                                    artwork = line.split(":", 1)[1].strip()
                            if artwork:
                                nowplaying_info["Artwork"] = artwork
                                global last_artwork
                                last_artwork = artwork
                                current_info["artwork_version"] += 1
                            if avc:
                                nowplaying_info["AVC"] = avc
                                global last_avc
                                last_avc = avc
                            if hevc:
                                nowplaying_info["HEVC"] = hevc
                                global last_hevc
                                last_hevc = hevc
                            print(artwork)
                        threading.Thread(target=fetch_artwork, args=(lookup_id,), daemon=True).start()
                        last_album_id = lookup_id

                # Only update nowplaying_info with cached values *after* checking for new artwork
                if last_artwork:
                    nowplaying_info["Artwork"] = last_artwork
                if last_avc:
                    nowplaying_info["AVC"] = last_avc
                if last_hevc:
                    nowplaying_info["HEVC"] = last_hevc

                artist_id = data.get("Artist ID")
                if artist_id:
                    if artist_id != nowplaying_info.get("Artist ID"):
                        def fetch_artist_art(artist_id):
                            result = subprocess.run(
                                ['python', 'artistart.py', str(artist_id)],
                                capture_output=True, text=True
                            )
                            print(f"artistart.py stdout:\n{result.stdout}")
                            print(f"artistart.py stderr:\n{result.stderr}")
                            global artist_art_url
                            for line in result.stdout.splitlines():
                                if line.startswith("ArtistArt:"):
                                    artist_art_url = line.split(":", 1)[1].strip()
                                    print(f"Captured ArtistArt URL: {artist_art_url}")
                                    nowplaying_info["ArtistArt"] = artist_art_url

                        threading.Thread(target=fetch_artist_art, args=(artist_id,), daemon=True).start()
            # Add duration and position to nowplaying_info
            duration, position = get_current_playback_info()
            if duration is not None and position is not None:
                nowplaying_info["Duration"] = duration
                nowplaying_info["Position"] = position
        except Exception:
            pass
        time.sleep(0.1)

@app.route("/")
def index():
    print(nowplaying_info.get("Artwork"))
    fresh_settings = load_settings()
    return render_template(
        "index.html",
        info=current_info,
        nowplaying=nowplaying_info,
        artwork=nowplaying_info.get("Artwork"),
        avc=nowplaying_info.get("AVC"),
        hevc=nowplaying_info.get("HEVC"),
        version=VERSION,
        default_visualizer=fresh_settings.get("default_visualizer", "visualizer1.js")
    )

@app.route("/vistest")
def vistest():
    print(nowplaying_info.get("Artwork"))
    return render_template(
        "vistest.html",
        info=current_info,
        nowplaying=nowplaying_info,
        artwork=nowplaying_info.get("Artwork"),
        avc=nowplaying_info.get("AVC"),
        hevc=nowplaying_info.get("HEVC")
    )

# New route for AJAX live data
@app.route("/data")
def data():
    return {
        "info": current_info,
        "nowplaying": nowplaying_info,
        "artwork_version": current_info["artwork_version"],
        "device": device_info,
        "artist_art": nowplaying_info.get("ArtistArt")
    }

# Flask route for player controls
@app.route("/player/<command>")
def player_control(command):
    music = SBApplication.applicationWithBundleIdentifier_("com.apple.Music")
    command = command.lower()
    if command == "play":
        music.playOnce_(None)
        return {"status": "playing"}
    elif command == "pause":
        music.pause()
        return {"status": "paused"}
    elif command == "next":
        music.nextTrack()
        return {"status": "next"}
    elif command == "previous":
        music.previousTrack()
        return {"status": "previous"}
    elif command == "shuffle_on":
        music.setShuffleEnabled_(True)
        return {"status": "shuffle_on"}
    elif command == "shuffle_off":
        music.setShuffleEnabled_(False)
        return {"status": "shuffle_off"}
    else:
        return {"error": "Invalid command"}, 400

# Function to periodically load device.json
def monitor_device_info():
    global device_info
    while True:
        try:
            with open("device.json", "r") as f:
                data = json.load(f)
                device_info.clear()
                device_info.update(data)
        except Exception:
            pass
        time.sleep(0.1)

@app.route("/visualizers")
def list_visualizers():
    visualizer_dir = os.path.join(app.static_folder, "visualizers")
    visualizers = []
    try:
        for filename in os.listdir(visualizer_dir):
            if not filename.endswith(".js"):
                continue
            file_path = os.path.join(visualizer_dir, filename)
            name = None
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                match = re.search(r"window\.visualizerName\s*=\s*['\"](.+?)['\"]", content)
                name = match.group(1) if match else os.path.splitext(filename)[0]
            except Exception:
                name = os.path.splitext(filename)[0]
            visualizers.append({
                "file": filename,
                "name": name
            })
        return {"visualizers": visualizers}
    except Exception as e:
        return {"error": str(e)}, 500


# Settings API
@app.route('/settings', methods=['GET'])
def get_settings():
    return jsonify(load_settings())

@app.route('/settings', methods=['POST'])
def update_settings():
    global settings
    new_settings = request.json
    save_settings(new_settings)
    settings = load_settings()
    print("✅ Settings reloaded:", settings)
    return jsonify({"status": "success"})

if __name__ == "__main__":
    subprocess.Popen(["python3", "device.py"])
    threading.Thread(target=monitor_sample_rate, daemon=True).start()
    threading.Thread(target=monitor_now_playing, daemon=True).start()
    threading.Thread(target=monitor_device_info, daemon=True).start()
    def open_browser_when_ready(url, timeout=10):
        for _ in range(timeout * 10):
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    webbrowser.get("safari").open(url)
                    return
            except Exception:
                pass
            time.sleep(0.1)


    port = settings.get("port", 22441)
    visualizer = settings.get("default_visualizer", "visualizer1.js")
    url = f"http://localhost:{port}"
    if settings.get("open_browser", True):  # default True for safety
        threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()

    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=port)
