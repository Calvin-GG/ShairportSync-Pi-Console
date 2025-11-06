#!/usr/bin/env python3
"""
Simple Tkinter UI for a Raspberry Pi 3.5" TFT touch screen.

Features:
- Displays track name, artist (from "comment" field), album.
- Shows the most recent cover art image from the cover art directory.
- Displays "Connect to receiver" when no AirPlay client is connected.
- Listens to the Shairport Sync metadata pipe for updates.

Notes / assumptions:
- Only one program should read the metadata pipe at a time to avoid conflicts.
- Pillow is required (listed in requirements.txt).

Run:
    python3 player_ui.py
"""

import os
import sys
import base64
import re
import threading
import time
from io import BytesIO
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk
except Exception as e:
    print("Tkinter not available. Ensure python3-tk is installed.")
    raise

try:
    from PIL import Image, ImageTk
except Exception:
    print("Pillow is required: pip install Pillow")
    raise

# --- Configuration ---
PIPE_PATH = "/tmp/shairport-sync-metadata"
COVER_ART_DIR = "/tmp/shairport-sync/.cache/coverart"
os.makedirs(COVER_ART_DIR, exist_ok=True)

ESSENTIAL_FIELDS = {
    "6d696e6d": "track_name",
    "61736370": "comment", #this is the artist, the artist pipeline was broken
    "6173616c": "album",
    "50494354": "picture_data"
}

# Shared state updated by metadata reader
current_song = {
    "track_name": None,
    "comment": None,
    "album": None,
    "picture_file": None,
    "last_update": 0,  # timestamp of last metadata update
}

buffer_lock = threading.Lock()

# --- Metadata listener ---
def metadata_listener(pipe_path=PIPE_PATH, cover_dir=COVER_ART_DIR):
    """Listen to the named pipe and update current_song dict."""
    print(f"Metadata listener starting. Pipe: {pipe_path}")
    buffer = ""
    while True:
        if not os.path.exists(pipe_path):
            time.sleep(1.0)
            continue
        try:
            with open(pipe_path, "r") as pipe:
                while True:
                    line = pipe.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    buffer += line.strip()

                    if buffer.endswith("</item>"):
                        length_match = re.search(r"<length>(\d+)</length>", buffer)
                        length = int(length_match.group(1)) if length_match else 0
                        if length == 0:
                            buffer = ""
                            continue

                        code_match = re.search(r"<code>(.*?)</code>", buffer)
                        data_match = re.search(r"<data encoding=\"base64\">(.*?)</data>", buffer)

                        if code_match and data_match:
                            code = code_match.group(1)
                            if code not in ESSENTIAL_FIELDS:
                                buffer = ""
                                continue

                            field_name = ESSENTIAL_FIELDS[code]
                            data_b64 = data_match.group(1)

                            try:
                                decoded_bytes = base64.b64decode(data_b64)

                                if field_name == "picture_data":
                                    try:
                                        img = Image.open(BytesIO(decoded_bytes))
                                        ext = img.format.lower() if img.format else "jpg"
                                        ts = int(time.time() * 1000)
                                        img_file = os.path.join(cover_dir, f"cover_art_{ts}.{ext}")
                                        img.save(img_file)
                                        with buffer_lock:
                                            current_song["picture_file"] = img_file
                                            current_song["last_update"] = time.time()
                                    except Exception as e:
                                        print("Error saving image:", e)
                                else:
                                    text = decoded_bytes.decode("utf-8", errors="replace")
                                    with buffer_lock:
                                        current_song[field_name] = text
                                        current_song["last_update"] = time.time()

                            except Exception as e:
                                print("Exception decoding item:", e)

                        buffer = ""
        except Exception as e:
            print("Metadata listener exception:", e)
            time.sleep(1.0)


# --- Helper to get most recent cover art file ---
def most_recent_cover(cover_dir=COVER_ART_DIR):
    p = Path(cover_dir)
    if not p.exists():
        return None
    candidates = [f for f in p.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp')]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return str(candidates[0])


# --- Tkinter UI ---
class PlayerUI(tk.Tk):
    def __init__(self, width=480, height=320, refresh_ms=1000):
        super().__init__()
        self.config(cursor="none")
        self.width = width
        self.height = height
        self.geometry(f"{self.width}x{self.height}+0+0")
        self.overrideredirect(True)
        self.title("CarPlay-style Player")
        self.configure(bg='#0a0a0a')
        self.resizable(False, False)

        self.refresh_ms = refresh_ms
        self.primary_color = '#ffffff'
        self.secondary_color = '#bdbdbd'

        self.art_frame = tk.Frame(self, bg='#0a0a0a')
        self.art_frame.place(relx=0.02, rely=0.05, relwidth=0.45, relheight=0.9)

        self.meta_frame = tk.Frame(self, bg='#0a0a0a')
        self.meta_frame.place(relx=0.5, rely=0.05, relwidth=0.48, relheight=0.9)

        self.art_label = tk.Label(self.art_frame, bg='#0a0a0a')
        self.art_label.pack(expand=True, fill='both')

        self.track_var = tk.StringVar(value='—')
        self.artist_var = tk.StringVar(value='—')
        self.album_var = tk.StringVar(value='—')

        self.track_lbl = tk.Label(self.meta_frame, textvariable=self.track_var,
                                  font=("Helvetica", 24, 'bold'), fg=self.primary_color,
                                  bg='#0a0a0a', wraplength=int(self.width*0.45))
        self.track_lbl.pack(anchor='w', pady=(10,0), padx=10)

        self.artist_lbl = tk.Label(self.meta_frame, textvariable=self.artist_var,
                                   font=("Helvetica", 14), fg=self.secondary_color,
                                   bg='#0a0a0a', wraplength=int(self.width*0.45))
        self.artist_lbl.pack(anchor='w', pady=(8,0), padx=10)

        self.album_lbl = tk.Label(self.meta_frame, textvariable=self.album_var,
                                  font=("Helvetica", 18, 'italic'), fg=self.secondary_color,
                                  bg='#0a0a0a', wraplength=int(self.width*0.45))
        self.album_lbl.pack(anchor='w', pady=(8,0), padx=10)

        self.current_image = None
        self.after(100, self.refresh_ui)

    def refresh_ui(self):
        with buffer_lock:
            track = current_song.get('track_name') or '—'
            artist = current_song.get('comment') or '—'
            album = current_song.get('album') or '—'
            picture_file = current_song.get('picture_file')
            last_update = current_song.get('last_update', 0)

        # Show "Connect to receiver" if no client connected
        if time.time() - last_update > 5:
            track = "Connect to Play Music"
            artist = "Open AirPlay on your device and select 'Receiver'"
            album = "made by calvin guerrero"
            picture_file = " /home/pi/airplay_player/airplaylogo.png"

        if not picture_file:
            picture_file = most_recent_cover()

        self.track_var.set(track)
        self.artist_var.set(artist)
        self.album_var.set(album)

        if picture_file and os.path.exists(picture_file):
            try:
                img = Image.open(picture_file).convert('RGBA')
                w = int(self.art_frame.winfo_width() or (self.width*0.45))
                h = int(self.art_frame.winfo_height() or (self.height*0.9))
                side = min(w, h)
                img = img.resize((side, side), Image.LANCZOS)
                tkimg = ImageTk.PhotoImage(img)
                self.current_image = tkimg
                self.art_label.configure(image=tkimg, text='')
            except Exception as e:
                self.art_label.configure(text='No art', image='', fg=self.secondary_color)
        else:
            self.art_label.configure(text='No art', image='', fg=self.secondary_color)

        self.after(self.refresh_ms, self.refresh_ui)


def start_metadata_thread():
    t = threading.Thread(target=metadata_listener, daemon=True)
    t.start()
    return t


def main():
    start_metadata_thread()
    app = PlayerUI(width=480, height=320, refresh_ms=1000)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
