import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import os
import json
import threading
import urllib.request
import zipfile
import tempfile
import shutil
import signal
import logging

BIN_DIR = os.path.join(os.path.expanduser("~"), ".mariotube")
if not os.path.exists(BIN_DIR):
    os.makedirs(BIN_DIR)

CONFIG_FILE = os.path.join(BIN_DIR, "config.json")
FFMPEG_BIN = os.path.join(BIN_DIR, "ffmpeg.exe")
YTDLP_BIN = os.path.join(BIN_DIR, "yt-dlp.exe")
config = {
    "output_folder": "",
    "ffmpeg_path": FFMPEG_BIN,
    "yt_dlp_path": YTDLP_BIN,
    "logging_enabled": False
}
current_processes = []

LOG_FILE = os.path.join(BIN_DIR, "mariotube.log")
logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO
)

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            # Add missing keys with defaults
            for k, v in config.items():
                if k not in loaded:
                    loaded[k] = v
            config = loaded
            save_config()

def is_ffmpeg_present():
    return os.path.isfile(FFMPEG_BIN)

def is_ytdlp_present():
    return os.path.isfile(YTDLP_BIN)

def download_with_progress(url, dest_path, popup, progress_var):
    try:
        with urllib.request.urlopen(url) as response, open(dest_path, "wb") as out_file:
            total = int(response.info().get("Content-Length", -1))
            downloaded = 0
            block_size = 8192
            while True:
                data = response.read(block_size)
                if not data:
                    break
                out_file.write(data)
                downloaded += len(data)
                if total > 0:
                    # Schedule progress update in main thread
                    popup.after(0, progress_var.set, downloaded / total * 100)
                    popup.after(0, popup.update_idletasks)
    except Exception as e:
        # Schedule error message in main thread
        popup.after(0, lambda: messagebox.showerror("Errore", f"Download fallito:\n{e}"))

def download_ffmpeg(popup, progress_var):
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    tmp_zip = os.path.join(tempfile.gettempdir(), "ffmpeg.zip")
    download_with_progress(url, tmp_zip, popup, progress_var)
    with zipfile.ZipFile(tmp_zip, 'r') as z:
        for m in z.namelist():
            if m.lower().endswith("ffmpeg.exe"):
                with z.open(m) as src, open(FFMPEG_BIN, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    os.remove(tmp_zip)
    config["ffmpeg_path"] = FFMPEG_BIN
    save_config()

def download_ytdlp(popup, progress_var):
    url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    download_with_progress(url, YTDLP_BIN, popup, progress_var)
    config["yt_dlp_path"] = YTDLP_BIN
    save_config()

def ensure_binaries(root):
    missing = []
    if not is_ffmpeg_present():
        missing.append("ffmpeg")
    if not is_ytdlp_present():
        missing.append("yt-dlp")
    if not missing:
        return

    popup = tk.Toplevel(root)
    popup.title("Download")
    tk.Label(popup, text="Scaricando: " + ", ".join(missing)).pack(pady=8)
    progress_var = tk.DoubleVar(value=0.0)
    progressbar = ttk.Progressbar(popup, orient="horizontal", length=280, mode="determinate", variable=progress_var)
    progressbar.pack(pady=6)

    def download_thread():
        try:
            if "ffmpeg" in missing:
                download_ffmpeg(popup, progress_var)
            if "yt-dlp" in missing:
                download_ytdlp(popup, progress_var)
            popup.after(0, popup.destroy)
            root.after(0, lambda: messagebox.showinfo("Download", "Download completato e pronto all'uso."))
        except Exception as e:
            popup.after(0, lambda: messagebox.showerror("Errore", f"Download fallito:\n{e}"))
            popup.after(0, popup.destroy)

    threading.Thread(target=download_thread, daemon=True).start()

def set_buttons_state(running):
    if running:
        button_go.config(state="disabled")
        button_stop.config(state="normal")
    else:
        button_go.config(state="normal" if video_var.get() or audio_var.get() else "disabled")
        button_stop.config(state="disabled")

def log_message(msg, level="info"):
    if config.get("logging_enabled", False):
        if level == "info":
            logging.info(msg)
        elif level == "error":
            logging.error(msg)

def log_subprocess_output(proc, prefix):
    if config.get("logging_enabled", False):
        out, _ = proc.communicate()
        for line in out.splitlines():
            log_message(f"{prefix}: {line.strip()}")

def run_program():
    global current_processes
    set_buttons_state(True)
    if not is_ytdlp_present():
        messagebox.showwarning("Eseguibile mancante", "yt-dlp.exe non trovato.")
        set_buttons_state(False)
        return
    url = entry.get().strip()
    if not url:
        messagebox.showwarning("Parametro mancante", "Inserisci un URL.")
        set_buttons_state(False)
        return

    env = os.environ.copy()
    env["PATH"] = BIN_DIR + os.pathsep + env.get("PATH", "")

    playlist_opt = ["--no-playlist"] if not playlist_var.get() else []
    output_template = os.path.join(config.get("output_folder", ""), "%(title)s.%(ext)s")
    yt_dlp_cmd = [
        YTDLP_BIN,
        *playlist_opt,
        "-f", "bestvideo+bestaudio/best",
        "-o", output_template,
        url
    ]

    def target():
        start_spinner()
        global current_processes
        out_folder = config.get("output_folder", "")
        before_files = set(os.listdir(out_folder))
        yt_proc = subprocess.Popen(
            yt_dlp_cmd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        current_processes.append(yt_proc)
        log_subprocess_output(yt_proc, "yt-dlp")
        yt_proc.wait()
        current_processes.remove(yt_proc)
        after_files = set(os.listdir(out_folder))
        new_files = [os.path.join(out_folder, f) for f in (after_files - before_files) if os.path.isfile(os.path.join(out_folder, f))]
        if not new_files:
            root.after(0, lambda: messagebox.showerror("Errore", "Nessun file scaricato trovato."))
            root.after(0, lambda: set_buttons_state(False))
            root.after(0, stop_spinner)
            return
        for downloaded_file in new_files:
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
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                current_processes.append(ffmpeg_proc)
                log_subprocess_output(ffmpeg_proc, "ffmpeg")
                ffmpeg_proc.wait()
                current_processes.remove(ffmpeg_proc)
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
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                current_processes.append(ffmpeg_proc)
                log_subprocess_output(ffmpeg_proc, "ffmpeg")
                ffmpeg_proc.wait()
                current_processes.remove(ffmpeg_proc)
            try:
                os.remove(downloaded_file)
            except Exception:
                pass
        root.after(0, stop_spinner)
        root.after(0, lambda: messagebox.showinfo("Completato", "Download e conversione completati."))
        root.after(0, lambda: set_buttons_state(False))

    threading.Thread(target=target, daemon=True).start()

def stop_program():
    global current_processes
    set_buttons_state(False)
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

def download_missing_binaries():
    missing = []
    if not is_ffmpeg_present():
        missing.append("FFmpeg")
    if not is_ytdlp_present():
        missing.append("yt-dlp")
    if not missing:
        return

    answer = messagebox.askyesno("Download mancanti", "I seguenti programmi sono mancanti e devono essere scaricati:\n" + "\n".join(missing) + "\nVuoi scaricarli ora?")
    if not answer:
        return

    popup = tk.Toplevel(root)
    popup.title("Download")
    tk.Label(popup, text="Scaricando: " + ", ".join(missing)).pack(pady=8)
    progress_var = tk.DoubleVar(value=0.0)
    progressbar = ttk.Progressbar(popup, orient="horizontal", length=280, mode="determinate", variable=progress_var)
    progressbar.pack(pady=6)

    def download_thread():
        try:
            if "FFmpeg" in missing:
                download_ffmpeg(popup, progress_var)
            if "yt-dlp" in missing:
                download_ytdlp(popup, progress_var)
            popup.after(0, popup.destroy)
            root.after(0, lambda: messagebox.showinfo("Download", "Download completato e pronto all'uso."))
        except Exception as e:
            popup.after(0, lambda: messagebox.showerror("Errore", f"Download fallito:\n{e}"))
            popup.after(0, popup.destroy)

    threading.Thread(target=download_thread, daemon=True).start()

def update_output_folder_label():
    output_folder_label.config(text=f"Cartella output: {config.get('output_folder', '')}")

def set_output_folder():
    folder_path = filedialog.askdirectory(title="Seleziona cartella di output")
    if folder_path:
        config["output_folder"] = folder_path
        save_config()
        update_output_folder_label()

def update_go_button_state():
    button_go.config(state="normal" if video_var.get() or audio_var.get() else "disabled")

# --- UI ---
load_config()
root = tk.Tk()

output_folder_label = tk.Label(root, text=f"Cartella output: {config.get('output_folder', '')}", fg="blue")
output_folder_label.pack(pady=2)

def ask_output_folder_if_needed():
    if not config.get("output_folder"):
        set_output_folder()

ask_output_folder_if_needed()
ensure_binaries(root)
root.title("MarioTube Launcher")
root.geometry("500x220")

menubar = tk.Menu(root)
settings_menu = tk.Menu(menubar, tearoff=0)
settings_menu.add_command(label="Seleziona cartella output", command=set_output_folder)
menubar.add_cascade(label="Impostazioni", menu=settings_menu)
root.config(menu=menubar)

tk.Label(root, text="Inserisci l'url:").pack(pady=5)
entry = tk.Entry(root, width=60)
entry.pack(pady=5)

options_frame = tk.Frame(root)
options_frame.pack(pady=5)
playlist_var = tk.BooleanVar()
audio_var = tk.BooleanVar()
video_var = tk.BooleanVar(value=True)
tk.Checkbutton(options_frame, text="PLAYLIST COMPLETA", variable=playlist_var).pack(side="left", padx=5)
tk.Checkbutton(options_frame, text="AUDIO", variable=audio_var, command=update_go_button_state).pack(side="left", padx=5)
tk.Checkbutton(options_frame, text="VIDEO", variable=video_var, command=update_go_button_state).pack(side="left", padx=5)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)
button_go = tk.Button(button_frame, text="GO", command=run_program, bg="green", fg="white")
button_go.pack(side="left", padx=5)
button_stop = tk.Button(button_frame, text="STOP", command=stop_program, bg="red", fg="white")
button_stop.pack(side="left", padx=5)

spinner_label = tk.Label(root, text="", font=("Arial", 16), fg="orange")
spinner_label.pack(pady=2)

spinner_running = False
spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
spinner_index = 0

def start_spinner():
    global spinner_running, spinner_index
    spinner_running = True
    spinner_index = 0
    animate_spinner()

def stop_spinner():
    global spinner_running
    spinner_running = False
    spinner_label.config(text="")

def animate_spinner():
    global spinner_index
    if spinner_running:
        spinner_label.config(text=spinner_frames[spinner_index % len(spinner_frames)] + " In esecuzione...")
        spinner_index += 1
        root.after(100, animate_spinner)

update_go_button_state()
set_buttons_state(False)  # Ensure buttons are enabled at startup

version_label = tk.Label(root, text="Versione 0.1", anchor="se", fg="gray")
version_label.place(relx=1.0, rely=1.0, anchor="se")

root.mainloop()
