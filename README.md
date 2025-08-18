# mariotube
Program to simplify yt-dlp usage.

On startup it checks for yt-dlp and ffmpeg presence in the .mariotube folder inside the personal user folder.
Also asks the first time for an output folder (can be changed later using the dropdown menu).

## Features
The only options are:
- PLAYLIST COMPLETA: if checked it will download the entire playlist and not only the current video of the playlist
- AUDIO: if checked it will extract the .MP3
- VIDEO: if checked it will download the best video (with audio of course) available (will be merged using ffmpeg)

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


## To Do - Reminder
- I don't like very much the behaviour that opens a prompt everytime it needs to launch yt-dlp or ffmpeg. Maybe can be done better.
- Also I'm not sure that logging to file works very well... Needs some testing done by my dad LOL.