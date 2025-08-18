import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import json
import threading
import urllib.request
import zipfile
import tempfile
import shutil
import signal

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".mariotube")
FFMPEG_DIR = os.path.join(os.path.expanduser("~"), ".mariotube_ffmpeg")
FFMPEG_BIN = os.path.join(FFMPEG_DIR, "bin", "ffmpeg.exe")

config = {"exe_path": "", "output_folder": "", "ffmpeg_path": ""}
current_processes = []

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

def is_ffmpeg_present():
    return os.path.isfile(FFMPEG_BIN)

def download_ffmpeg():
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    tmp_zip = os.path.join(tempfile.gettempdir(), "ffmpeg.zip")
    with urllib.request.urlopen(url) as response, open(tmp_zip, "wb") as out_file:
        out_file.write(response.read())
    with zipfile.ZipFile(tmp_zip, 'r') as z:
        for m in z.namelist():
            if m.lower().endswith("ffmpeg.exe"):
                os.makedirs(os.path.dirname(FFMPEG_BIN), exist_ok=True)
                with z.open(m) as src, open(FFMPEG_BIN, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    os.remove(tmp_zip)
    config["ffmpeg_path"] = FFMPEG_BIN
    save_config()

def ensure_ffmpeg(root):
    if not is_ffmpeg_present():
        download_ffmpeg()
        messagebox.showinfo("ffmpeg", "ffmpeg scaricato e pronto all'uso.")

def run_program():
    global current_processes
    if not config.get("exe_path"):
        messagebox.showwarning("Eseguibile mancante", "Imposta il percorso dell'eseguibile.")
        return
    url = entry.get().strip()
    if not url:
        messagebox.showwarning("Parametro mancante", "Inserisci un URL.")
        return

    env = os.environ.copy()
    ffmpeg_bin_folder = os.path.dirname(FFMPEG_BIN)
    env["PATH"] = ffmpeg_bin_folder + os.pathsep + env.get("PATH", "")

    # Playlist option
    playlist_opt = ["--no-playlist"] if not playlist_var.get() else []

    # Download best video+audio (no merging, no extraction)
    output_template = os.path.join(config.get("output_folder", ""), "%(title)s.%(ext)s")
    yt_dlp_cmd = [
        config["exe_path"],
        *playlist_opt,
        "-f", "bestvideo+bestaudio/best",
        "-o", output_template,
        url
    ]

    def target():
        global current_processes
        out_folder = config.get("output_folder", "")
        # 1. List files before download
        before_files = set(os.listdir(out_folder))

        # 2. Download with yt-dlp
        yt_proc = subprocess.Popen(
            yt_dlp_cmd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            env=env
        )
        current_processes.append(yt_proc)
        yt_proc.wait()
        current_processes.remove(yt_proc)

        # 3. List files after download
        after_files = set(os.listdir(out_folder))
        new_files = [os.path.join(out_folder, f) for f in (after_files - before_files) if os.path.isfile(os.path.join(out_folder, f))]

        if not new_files:
            messagebox.showerror("Errore", "Nessun file scaricato trovato.")
            return

        # 4. Process each new file
        for downloaded_file in new_files:
            # VIDEO: convert to mp4
            if video_var.get():
                mp4_file = os.path.splitext(downloaded_file)[0] + ".mp4"
                ffmpeg_cmd = [
                    FFMPEG_BIN,
                    "-i", downloaded_file,
                    "-c:v", "copy",
                    "-c:a", "copy",
                    mp4_file
                ]
                ffmpeg_proc = subprocess.Popen(
                    ffmpeg_cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    env=env
                )
                current_processes.append(ffmpeg_proc)
                ffmpeg_proc.wait()
                current_processes.remove(ffmpeg_proc)
            # AUDIO: extract mp3
            if audio_var.get():
                mp3_file = os.path.splitext(downloaded_file)[0] + ".mp3"
                ffmpeg_cmd = [
                    FFMPEG_BIN,
                    "-i", downloaded_file,
                    "-q:a", "0",
                    "-map", "a",
                    mp3_file
                ]
                ffmpeg_proc = subprocess.Popen(
                    ffmpeg_cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    env=env
                )
                current_processes.append(ffmpeg_proc)
                ffmpeg_proc.wait()
                current_processes.remove(ffmpeg_proc)
            # Remove original file
            try:
                os.remove(downloaded_file)
            except Exception:
                pass

        messagebox.showinfo("Completato", "Download e conversione completati.")

    threading.Thread(target=target, daemon=True).start()

def stop_program():
    global current_processes
    killed = False
    for proc in current_processes[:]:
        if proc.poll() is None:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            killed = True
    current_processes.clear()
    if killed:
        messagebox.showinfo("STOP", "Tutti i processi yt-dlp e ffmpeg sono stati terminati.")
    else:
        messagebox.showinfo("STOP", "Nessun processo da terminare.")

def set_executable():
    file_path = filedialog.askopenfilename(title="Seleziona yt-dlp.exe", filetypes=[("yt-dlp", "yt-dlp.exe")])
    if file_path:
        config["exe_path"] = file_path
        save_config()

def set_output_folder():
    folder_path = filedialog.askdirectory(title="Seleziona cartella di output")
    if folder_path:
        config["output_folder"] = folder_path
        save_config()

# --- UI ---
load_config()
root = tk.Tk()
ensure_ffmpeg(root)
root.title("MarioTube Launcher")
root.geometry("500x220")

menubar = tk.Menu(root)
settings_menu = tk.Menu(menubar, tearoff=0)
settings_menu.add_command(label="Imposta eseguibile", command=set_executable)
settings_menu.add_command(label="Seleziona cartella output", command=set_output_folder)
menubar.add_cascade(label="Impostazioni", menu=settings_menu)
root.config(menu=menubar)

tk.Label(root, text="Inserisci il parametro:").pack(pady=5)
entry = tk.Entry(root, width=60)
entry.pack(pady=5)

options_frame = tk.Frame(root)
options_frame.pack(pady=5)
playlist_var = tk.BooleanVar()
audio_var = tk.BooleanVar()
video_var = tk.BooleanVar(value=True)
tk.Checkbutton(options_frame, text="PLAYLIST COMPLETA", variable=playlist_var).pack(side="left", padx=5)
tk.Checkbutton(options_frame, text="AUDIO", variable=audio_var).pack(side="left", padx=5)
tk.Checkbutton(options_frame, text="VIDEO", variable=video_var).pack(side="left", padx=5)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)
tk.Button(button_frame, text="GO", command=run_program, bg="green", fg="white").pack(side="left", padx=5)
tk.Button(button_frame, text="STOP", command=stop_program, bg="red", fg="white").pack(side="left", padx=5)

root.mainloop()
