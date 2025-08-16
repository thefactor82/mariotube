import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import json
import threading
import base64
import urllib.request
import zipfile
import tempfile
import shutil
import sys

# Percorsi file
config_file = os.path.join(os.path.expanduser("~"), ".mariotube")
pid_file = os.path.join(os.path.expanduser("~"), ".mariotube.pid")

# Config iniziale
config = {"exe_path": "", "output_folder": "", "ffmpeg_path": ""}
current_process = None

# GIF animata in base64 (icona di caricamento)
loading_gif_data = b"""
R0lGODlhEAAQAPQAAP///wAAAMLCwkJCQqioqPf39+/v7+bm5oSEhJ+fn729vcPDw5ycnOTk5NjY
2MLCwsHBwZiYmIaGhvr6+vf39yYmJmZmZra2tp6enoiIiPLy8q6urmZmZoCAgP///wAAAAAAAAAA
AAAAACH5BAAAAAAALAAAAAAQABAAAAW74CeOZGmeaKqubOtCzPQh2nCwAIfJzJaoKguWAwHCzvuz
svoG+G4F0n5eIhjDQa9QoFMvwWZ1KyxKpVqtFrvfn9rq9Nq/V6/X6/QKBADs=
"""

# Cartella di installazione ffmpeg standalone
FFMPEG_DIR = os.path.join(os.path.expanduser("~"), ".mariotube_ffmpeg")
FFMPEG_BIN_PATH = os.path.join(FFMPEG_DIR, "bin", "ffmpeg.exe")  # Windows path

def is_ffmpeg_present():
    """
    Controlla se ffmpeg esiste e se è eseguibile.
    Se non esiste nel percorso atteso, ricerca sotto FFMPEG_DIR.
    """
    global FFMPEG_BIN_PATH

    # 1) controllo diretto sul path previsto
    if os.path.isfile(FFMPEG_BIN_PATH):
        try:
            res = subprocess.run([FFMPEG_BIN_PATH, "-version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return True
            # se c'è il file ma non è eseguibile, consideriamolo assente
        except Exception:
            pass

    # 2) fallback: cerca ffmpeg.exe in tutta la cartella FFMPEG_DIR (se esiste)
    if os.path.isdir(FFMPEG_DIR):
        for root, _, files in os.walk(FFMPEG_DIR):
            if "ffmpeg.exe" in files:
                candidate = os.path.join(root, "ffmpeg.exe")
                try:
                    res = subprocess.run([candidate, "-version"], capture_output=True, text=True, timeout=5)
                    if res.returncode == 0:
                        # aggiorna il path usato dal programma
                        FFMPEG_BIN_PATH = candidate
                        # salva in config così compare nelle impostazioni
                        config["ffmpeg_path"] = FFMPEG_BIN_PATH
                        salva_impostazioni()
                        return True
                except Exception:
                    continue

    return False

def download_ffmpeg(progress_callback=None):
    """
    Scarica ffmpeg statico Windows da gyan.dev e lo estrae in FFMPEG_BIN_PATH.
    Estrae singolarmente ffmpeg.exe (e ffprobe.exe se presente), indipendentemente
    dalla struttura delle cartelle interne allo zip.
    """
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    try:
        tmp_zip_path = os.path.join(tempfile.gettempdir(), "ffmpeg_mariotube.zip")
        with urllib.request.urlopen(url) as response, open(tmp_zip_path, "wb") as out_file:
            total_length = response.length or 0
            downloaded = 0
            block_size = 8192
            while True:
                data = response.read(block_size)
                if not data:
                    break
                out_file.write(data)
                downloaded += len(data)
                if progress_callback and total_length:
                    try:
                        progress_callback(downloaded / total_length * 100)
                    except Exception:
                        pass

        # Apro lo zip e cerco i membri che terminano con ffmpeg.exe / ffprobe.exe
        extracted_any = False
        with zipfile.ZipFile(tmp_zip_path, 'r') as z:
            members = z.namelist()
            ffmpeg_member = None
            ffprobe_member = None
            for m in members:
                lm = m.lower()
                if lm.endswith("ffmpeg.exe"):
                    ffmpeg_member = m
                if lm.endswith("ffprobe.exe"):
                    ffprobe_member = m

            # Creo la cartella bin dove salvare i file
            bin_dir = os.path.dirname(FFMPEG_BIN_PATH)
            os.makedirs(bin_dir, exist_ok=True)

            if ffmpeg_member:
                with z.open(ffmpeg_member) as source, open(FFMPEG_BIN_PATH, "wb") as target:
                    shutil.copyfileobj(source, target)
                extracted_any = True

            if ffprobe_member:
                ffprobe_path = os.path.join(bin_dir, "ffprobe.exe")
                with z.open(ffprobe_member) as source, open(ffprobe_path, "wb") as target:
                    shutil.copyfileobj(source, target)
                extracted_any = True

        # pulizia
        try:
            os.remove(tmp_zip_path)
        except Exception:
            pass

        if not extracted_any:
            raise Exception("ffmpeg.exe non trovato nell'archivio scaricato.")

        # prova a lanciare ffmpeg per verificare
        try:
            res = subprocess.run([FFMPEG_BIN_PATH, "-version"], capture_output=True, text=True, timeout=5)
            if res.returncode != 0:
                raise Exception("ffmpeg scaricato ma non eseguibile.")
        except Exception as e:
            raise

        # aggiorna config e salva
        config["ffmpeg_path"] = FFMPEG_BIN_PATH
        salva_impostazioni()
        return True

    except Exception as e:
        # non usare messagebox direttamente qui (chiamante provvederà) ma lo teniamo per compatibilità
        try:
            messagebox.showerror("Errore", f"Download o estrazione ffmpeg fallito:\n{e}")
        except Exception:
            pass
        return False

def ensure_ffmpeg(root):
    # se già presente e funzionante, esci
    if is_ffmpeg_present():
        # aggiorna config se necessario
        config["ffmpeg_path"] = FFMPEG_BIN_PATH
        salva_impostazioni()
        return

    # se il file esiste ma non funziona, proviamo a rimuoverlo così scarichiamo da zero
    if os.path.isfile(FFMPEG_BIN_PATH):
        try:
            os.remove(FFMPEG_BIN_PATH)
        except Exception:
            pass

    popup = tk.Toplevel(root)
    popup.title("Download ffmpeg")
    popup.geometry("320x110")
    popup.resizable(False, False)
    label = tk.Label(popup, text="Scaricando ffmpeg, attendere...")
    label.pack(pady=8)
    progress_var = tk.DoubleVar(value=0.0)

    # usa ttk.Progressbar (assicurati di avere importato ttk prima di chiamare questa funzione)
    progressbar = ttk.Progressbar(popup, orient="horizontal", length=280, mode="determinate", variable=progress_var)
    progressbar.pack(pady=6)

    # stato condiviso
    download_info = {"percent": 0.0, "done": False, "success": False, "error": None}

    def progress_callback(percent):
        download_info["percent"] = percent

    def download_thread():
        try:
            success = download_ffmpeg(progress_callback)
            download_info["success"] = success
        except Exception as e:
            download_info["error"] = str(e)
        finally:
            download_info["done"] = True

    threading.Thread(target=download_thread, daemon=True).start()

    def check_progress():
        progress_var.set(download_info["percent"])
        if download_info["done"]:
            popup.destroy()
            if download_info["error"]:
                root.after(0, lambda: messagebox.showerror("Errore", f"Download o estrazione ffmpeg fallito:\n{download_info['error']}"))
            elif download_info["success"]:
                # aggiorna config con il path effettivo e salva
                config["ffmpeg_path"] = FFMPEG_BIN_PATH
                salva_impostazioni()
                root.after(0, lambda: messagebox.showinfo("ffmpeg", "ffmpeg scaricato correttamente e pronto all'uso."))
            else:
                root.after(0, lambda: messagebox.showwarning("ffmpeg", "ffmpeg non è stato scaricato, alcune funzionalità potrebbero non funzionare."))
        else:
            popup.after(100, check_progress)

    check_progress()
    root.wait_window(popup)

def load_gif_frames(data):
    from tkinter import PhotoImage
    frames = []
    raw_data = base64.b64decode(data)
    frame_index = 0
    while True:
        try:
            frame = PhotoImage(data=raw_data, format=f"gif -index {frame_index}")
            frames.append(frame)
            frame_index += 1
        except tk.TclError:
            break
    return frames


# Variabili globali GIF e animazione
gif_frames = []
gif_index = 0
gif_running = False
gif_label = None

def salva_impostazioni():
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile salvare la configurazione:\n{e}")

def carica_impostazioni():
    global config, FFMPEG_BIN_PATH
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            # se nel config c'è ffmpeg_path e il file esiste, usalo
            ffconf = config.get("ffmpeg_path")
            if ffconf:
                if os.path.isfile(ffconf):
                    FFMPEG_BIN_PATH = ffconf
                else:
                    # se il path salvato non è valido, lo rimuoviamo dalla config
                    config["ffmpeg_path"] = ""
        except Exception:
            messagebox.showwarning("Errore", "Impossibile leggere il file di configurazione. Verrà ricreato.")

def set_executable():
    file_path = filedialog.askopenfilename(
        title="Seleziona yt-dlp.exe",
        filetypes=[("yt-dlp", "yt-dlp.exe")],
    )
    if file_path:
        config["exe_path"] = file_path
        salva_impostazioni()
        messagebox.showinfo("Impostazioni salvate", f"Eseguibile impostato:\n{file_path}")

def set_output_folder():
    folder_path = filedialog.askdirectory(title="Seleziona cartella di output")
    if folder_path:
        config["output_folder"] = folder_path
        salva_impostazioni()
        messagebox.showinfo("Impostazioni salvate", f"Cartella output impostata:\n{folder_path}")

def start_loading_animation():
    global gif_running, gif_index
    gif_running = True
    gif_index = 0
    gif_label.place(x=440, y=70)  # Posizione vicino a pulsanti GO/STOP
    animate_gif()

def animate_gif():
    global gif_index
    if gif_running and gif_frames:
        frame = gif_frames[gif_index]
        gif_label.config(image=frame)
        gif_index = (gif_index + 1) % len(gif_frames)
        root.after(100, animate_gif)

def stop_loading_animation():
    global gif_running
    gif_running = False
    gif_label.place_forget()

def run_program():
    """Scarica sempre il file MP4 e poi crea/conserva i formati desiderati."""
    global current_process

    if not config.get("exe_path"):
        messagebox.showwarning("Eseguibile mancante", "Prima imposta il percorso dell'eseguibile dalle impostazioni.")
        return

    url = entry.get().strip()
    if not url:
        messagebox.showwarning("Parametro mancante", "Inserisci un URL prima di continuare.")
        return

    def target():
        global current_process
        try:
            print("\n[DEBUG] Avvio processo...")
            print(f"[DEBUG] URL inserito: {url}")
            print(f"[DEBUG] Percorso exe yt-dlp: {config.get('exe_path')}")
            print(f"[DEBUG] Output folder: {config.get('output_folder', '')}")

            # Percorso ffmpeg (se presente)
            ffmpeg_path = FFMPEG_BIN_PATH if is_ffmpeg_present() else None
            print(f"[DEBUG] ffmpeg_path: {ffmpeg_path}")

            # Comando per scaricare sempre MP4 con il miglior video+audio
            output_template = os.path.join(config.get("output_folder", ""), "%(title)s.%(ext)s")
            print(f"[DEBUG] Output template: {output_template}")

            cmd = [
                config["exe_path"],
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
                "-o", output_template
            ]

            if not playlist_var:  # aggiunge l'opzione solo se playlist_var è False
                cmd.insert(1, "--no-playlist")  # inserisce "--no-playlist" subito dopo il percorso dell'eseguibile


            if ffmpeg_path:
                cmd.extend(["--ffmpeg-location", ffmpeg_path])


            cmd.append(url)
            print(f"[DEBUG] Comando yt-dlp: {cmd}")

            # Scarica il file MP4
            if os.name == "nt":
                current_process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                current_process = subprocess.Popen(cmd)
            current_process.wait()

            # Individua il file mp4 scaricato
            folder = config.get("output_folder", "")
            print(f"[DEBUG] Cartella di ricerca file: {folder}")
            mp4_file = None
            for file in os.listdir(folder):
                print(f"[DEBUG] File trovato: {file}")
                if file.endswith(".mp4"):
                    mp4_file = os.path.join(folder, file)
                    break

            print(f"[DEBUG] File MP4 individuato: {mp4_file}")

            if not mp4_file:
                messagebox.showerror("Errore", "Nessun file MP4 trovato dopo il download.")
                return

            # Se serve solo AUDIO -> estrai MP3 e rimuovi MP4
            if audio_var.get() and not video_var.get():
                mp3_file = mp4_file.rsplit(".", 1)[0] + ".mp3"
                print(f"[DEBUG] Converto in MP3: {mp3_file}")
                subprocess.run([ffmpeg_path or "ffmpeg", "-i", mp4_file, "-q:a", "0", "-map", "a", mp3_file])
                os.remove(mp4_file)
                print("[DEBUG] MP4 originale eliminato.")

            # Se serve solo VIDEO -> tieni MP4, nessuna conversione
            elif video_var.get() and not audio_var.get():
                print("[DEBUG] Solo video richiesto, nessuna conversione aggiuntiva.")

            # Se servono entrambi -> crea MP3 e tieni MP4
            elif audio_var.get() and video_var.get():
                mp3_file = mp4_file.rsplit(".", 1)[0] + ".mp3"
                print(f"[DEBUG] Creo anche MP3: {mp3_file}")
                subprocess.run([ffmpeg_path or "ffmpeg", "-i", mp4_file, "-q:a", "0", "-map", "a", mp3_file])

        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile avviare il processo:\n{e}")
            print(f"[DEBUG][ERRORE] {e}")
        finally:
            stop_loading_animation()
            print("[DEBUG] Fine processo.")

    start_loading_animation()
    threading.Thread(target=target, daemon=True).start()


def stop_program():
    """Termina il processo (preferibilmente albero di processi) e ferma animazione."""
    global current_process
    pid = None

    # Prima preferiamo processo corrente se attivo
    if current_process and current_process.poll() is None:
        pid = current_process.pid
    else:
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r", encoding="utf-8") as f:
                    pid_text = f.read().strip()
                    if pid_text:
                        pid = int(pid_text)
            except Exception:
                pid = None

    if pid is not None:
        try:
            res = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                                 capture_output=True, text=True)
            if res.returncode == 0:
                messagebox.showinfo("STOP", f"Processo {pid} terminato con successo.")
            else:
                ask = messagebox.askyesno("Processo non trovato",
                                          f"Non sono riuscito a terminare il PID {pid}.\n"
                                          "Vuoi terminare comunque TUTTI i processi 'yt-dlp.exe' attivi?")
                if ask:
                    res2 = subprocess.run(["taskkill", "/F", "/IM", "yt-dlp.exe", "/T"],
                                          capture_output=True, text=True)
                    if res2.returncode == 0:
                        messagebox.showinfo("STOP", "Tutti i processi 'yt-dlp.exe' terminati.")
                    else:
                        messagebox.showerror("Errore", f"Impossibile terminare i processi per nome.\n{res2.stderr}")
                else:
                    messagebox.showinfo("STOP", "Operazione annullata.")
        except FileNotFoundError:
            # Fallback se taskkill non presente (non Windows)
            if current_process and current_process.poll() is None:
                try:
                    current_process.terminate()
                    current_process.wait(timeout=5)
                    messagebox.showinfo("STOP", "Processo terminato.")
                except Exception as e:
                    messagebox.showerror("Errore", f"Impossibile terminare il processo:\n{e}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la terminazione:\n{e}")
    else:
        ask_all = messagebox.askyesno("Nessun processo noto",
                                      "Non trovo un processo avviato da questo launcher.\n"
                                      "Vuoi terminare TUTTI i processi 'yt-dlp.exe' attivi?")
        if ask_all:
            try:
                res2 = subprocess.run(["taskkill", "/F", "/IM", "yt-dlp.exe", "/T"],
                                      capture_output=True, text=True)
                if res2.returncode == 0:
                    messagebox.showinfo("STOP", "Tutti i processi 'yt-dlp.exe' terminati.")
                else:
                    messagebox.showerror("Errore", f"Impossibile terminare i processi per nome.\n{res2.stderr}")
            except Exception as e:
                messagebox.showerror("Errore", f"Operazione fallita:\n{e}")
        else:
            messagebox.showinfo("STOP", "Operazione annullata.")

    current_process = None
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    except Exception:
        pass
    stop_loading_animation()
    update_buttons()

def update_buttons():
    running = False
    if current_process and current_process.poll() is None:
        running = True
    button_go.config(state="normal" if not running else "disabled")
    button_stop.config(state="normal" if running else "disabled")
    root.after(500, update_buttons)

def mostra_impostazioni():
    info = (
        f"Eseguibile yt-dlp: {config.get('exe_path') or '(non impostato)'}\n"
        f"Cartella output: {config.get('output_folder') or '(non impostata)'}\n"
        f"ffmpeg: {config.get('ffmpeg_path') or '(non installato)'}"
    )
    messagebox.showinfo("Impostazioni correnti", info)

# --- Inizio UI ---
carica_impostazioni()

root = tk.Tk()
import tkinter.ttk as ttk
ensure_ffmpeg(root)

root.title("MarioTube Launcher")
root.geometry("500x180")

menubar = tk.Menu(root)
settings_menu = tk.Menu(menubar, tearoff=0)
settings_menu.add_command(label="Imposta eseguibile", command=set_executable)
settings_menu.add_command(label="Seleziona cartella output", command=set_output_folder)
settings_menu.add_command(label="Visualizza impostazioni", command=mostra_impostazioni)
menubar.add_cascade(label="Impostazioni", menu=settings_menu)
root.config(menu=menubar)

tk.Label(root, text="Inserisci il parametro:").pack(pady=5)
entry = tk.Entry(root, width=60)
entry.pack(pady=5)

playlist_var = tk.BooleanVar(value=False)
audio_var = tk.BooleanVar(value=False)
video_var = tk.BooleanVar(value=True)

options_frame = tk.Frame(root)
options_frame.pack()

tk.Checkbutton(options_frame, text="PLAYLIST COMPLETA", variable=playlist_var).pack(side="left", padx=5)
tk.Checkbutton(options_frame, text="AUDIO", variable=audio_var).pack(side="left", padx=5)
tk.Checkbutton(options_frame, text="VIDEO", variable=video_var).pack(side="left", padx=5)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

button_go = tk.Button(button_frame, text="GO", command=run_program,
                      bg="green", fg="white", font=("Arial", 12, "bold"))
button_go.pack(side="left", padx=5)

button_stop = tk.Button(button_frame, text="STOP", command=stop_program,
                        bg="red", fg="white", font=("Arial", 12, "bold"))
button_stop.pack(side="left", padx=5)

gif_frames = load_gif_frames(loading_gif_data)
gif_label = tk.Label(root)

update_buttons()

root.mainloop()
