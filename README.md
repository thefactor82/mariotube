# mariotube
Program to simplify yt-dlp usage.

On startup it checks for yt-dlp, ffmpeg and deno presence in the .mariotube folder inside the personal user folder, and updates yt-dlp to the latest version if available.
Also asks the first time for an output folder (can be changed later using the dropdown menu).

Note: deno is used by yt-dlp as a JavaScript runtime to pass YouTube's anti-bot checks (without it YouTube videos may result in "This video is not available").

## Features
The only options are:
- AUDIO: if checked it will extract the .MP3
- VIDEO: if checked it will download the best video (with audio of course) available (will be merged using ffmpeg)

The URL field is "smart": dirty URLs (extra params, playlists, share links, short links) are cleaned automatically to the plain video URL.
If the URL points to a playlist, only the first video is downloaded.
Logs are written daily to `~/.mariotube/mariotube.log` (previous day's log is discarded at startup) for troubleshooting.

## Building with GitHub Actions
Pushing a tag like `v1.0.0` triggers the workflow `.github/workflows/release.yml`, which builds the executable with PyInstaller and creates a GitHub release with `mariotube.exe` and `mariotube.zip` attached.

## Dev Requirements
Python for Windows (Tkinter already installed)

To compile you need to install pyinstaller via Powershell:

```powershell
pip install pyinstaller
```

Then, from inside the project folder:

```powershell
pyinstaller --onefile --noconsole --icon=logo.ico mariotube.py
```