Player UI for Shairport Sync Metadata (Tkinter)
by: calvin guerrero

What this is
------------
A single-file Tkinter UI (`player_ui.py`) designed for a Raspberry Pi 3.5" TFT touch screen. It displays:

- Track name
- Artist (the `comment` metadata field)
- Album
- Album artwork (the most recent image found in the Shairport cover art cache directory)

This is meant to be run on a Raspberry Pi with a 3.5 inch tft display. I used a Raspberry Pi 3b+ and a Microcenter tft hat. 

How it gets data
----------------
The UI listens to the Shairport Sync metadata named pipe at `/tmp/shairport-sync-metadata`. It also looks for saved cover art images in `/tmp/shairport-sync/.cache/coverart` and will display the most recent image there.

Important assumptions and notes
-----------------------------
- The Shairport Sync metadata pipe is intended for a single reader. If you have another program reading the metadata pipe, stop it before running `player_ui.py` to avoid conflicts. If two programs read the pipe at once, metadata may be split between them unpredictably.
- Pillow is required for image handling. Install with `pip3 install -r requirements.txt`
- Tkinter must be available on the system (install `python3-tk` or the platform equivalent if missing).

Usage
-----
1. Install dependencies:

```bash
pip3 install -r requirements.txt
```

2. Make sure Shairport Sync is configured to write metadata to `/tmp/shairport-sync-metadata` or change `PIPE_PATH` in `player_ui.py`.

3. Run the UI:

```bash
python3 player_ui.py
```

4. (optional) add the script to start on boot

If you prefer the UI not to listen to the metadata pipe (for example, if another metadata consumer is already running), the UI will still display the most recent image from `/tmp/shairport-sync/.cache/coverart` and uses placeholder text for metadata if none was read.

Customization
-------------
- Edit `PIPE_PATH` and `COVER_ART_DIR` at the top of `player_ui.py` to match your environment. (these should be fine by default, only change if you know what youre doing)

- The window size defaults to 480x320 which fits many 3.5" TFT HATs; change the `PlayerUI(width=..., height=...)` call in `main()` to adapt.

Troubleshooting
---------------
- If no artwork appears, verify that images are being saved to `/tmp/shairport-sync/.cache/coverart` and that files have image extensions (.jpg/.jpeg/.png).
- If the UI reports that the pipe is missing, ensure Shairport Sync metadata output is enabled and the pipe path matches `PIPE_PATH`.


Current issues / Future enhancements (in case anyone wants to try and fix them)
-------
- There is no graceful handling if tracks are missing a title, comment (which is artist), album, or album artwork. Therefore it will use the last cached version of these. Graceful handling is not something I plan on implementing, but this is a non issue for 99% of songs on Apple Music.

- There is a 10 minute no-update debounce that resets the airplay connect message after 10 minutes of no updates. This should be fine for most songs, but the most graceful way to handle this is to poll updates from shairport. 

- The artist pipeline would send garbled data half the time, so i resorted to using the comment  instead. 

- This has been tested working on Soundcloud and Apple Music. Other music support is not guaranteed (but im sure it should work)

License
-------
MIT-style. Use at your own risk. ZERO WARRANTY
Any reference to any Apple Trademarks are purely educational and / or entertainment-related. All Apple-registered trademarks are property of Apple, INC. 
Any song referenced is owned by its respective copyright holder, not myself. I do not claim ownership of any songs used in this github. 
