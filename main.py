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
from io import BytesIO
import base64
import hashlib
import subprocess

def floats_differ(a, b, epsilon=1e-3):
    return abs(a - b) > epsilon

app = Flask(__name__)
import logging
werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.INFO)  # Enable GET logs

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
                        subprocess.run(['./srswitch.swift', str(sample_rate)])

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
                if album_id:
                    if album_id != last_album_id:
                        def fetch_artwork(album_id):
                            result = subprocess.run(
                                ['python', 'artwork.py', '--album-id', str(album_id)],
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

                        threading.Thread(target=fetch_artwork, args=(album_id,), daemon=True).start()
                        last_album_id = album_id

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
        time.sleep(0.01)

@app.route("/")
def index():
    print(nowplaying_info.get("Artwork"))
    return render_template(
        "index.html",
        info=current_info,
        nowplaying=nowplaying_info,
        artwork=nowplaying_info.get("Artwork"),
        avc=nowplaying_info.get("AVC"),
        hevc=nowplaying_info.get("HEVC")
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
    try:
        files = [f for f in os.listdir(visualizer_dir) if f.endswith(".js")]
        return {"visualizers": files}
    except Exception as e:
        return {"error": str(e)}, 500

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

    threading.Thread(target=open_browser_when_ready, args=("http://localhost:22441/?visualizer=visualizer4.js",), daemon=True).start()
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=22441)
