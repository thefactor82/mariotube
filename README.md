# mariotube
Program to simplify yt-dlp usage

# REQUIREMENTS
Python for Windows (Tkinter already installed)

To compile you need to install pyinstaller via Powershell:

```powershell
pip install pyinstaller
```

Then, from inside the project folder:

```powershell
pyinstaller --onefile --noconsole --icon=logo.ico mariotube.py
```


# TO DO
I don't like very much the behaviour that opens a prompt everytime it needs to launch yt-dlp or ffmpeg. Maybe can be done better.