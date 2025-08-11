import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import json
import threading
import base64

# Percorsi file
config_file = os.path.join(os.path.expanduser("~"), ".mariotube")
pid_file = os.path.join(os.path.expanduser("~"), ".mariotube.pid")

# Config iniziale
config = {"exe_path": "", "output_folder": ""}
current_process = None

# GIF animata in base64 (icona di caricamento)
loading_gif_data = b"""
R0lGODlhEAAQAPQAAP///wAAAMLCwkJCQqioqPf39+/v7+bm5oSEhJ+fn729vcPDw5ycnOTk5NjY
2MLCwsHBwZiYmIaGhvr6+vf39yYmJmZmZra2tp6enoiIiPLy8q6urmZmZoCAgP///wAAAAAAAAAA
AAAAACH5BAAAAAAALAAAAAAQABAAAAW74CeOZGmeaKqubOtCzPQh2nCwAIfJzJaoKguWAwHCzvuz
svoG+G4F0n5eIhjDQa9QoFMvwWZ1KyxKpVqtFrvfn9rq9Nq/V6/X6/QKBADs=
"""

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
    global config
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
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
    """Avvia yt-dlp in un thread separato con opzioni e animazione."""
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
            cmd = [config["exe_path"]]

            # Playlist
            if not playlist_var.get():
                cmd.append("--no-playlist")

            # Audio/Video opzioni
            if audio_var.get() and not video_var.get():
                cmd.extend(["-f", "bestaudio", "--extract-audio", "--audio-format", "mp3"])
            elif video_var.get() and not audio_var.get():
                # Forza miglior formato unico (non separato)
                cmd.extend(["-f", "best"])
            elif audio_var.get() and video_var.get():
                # Scarica video e audio separati -> serve ffmpeg!
                cmd.extend(["-f", "best", "--extract-audio", "--audio-format", "mp3"])
                # Se vuoi usare ffmpeg incluso, aggiungi:
                # cmd.extend(["--ffmpeg-location", "ffmpeg_bin"])

            # Output folder
            if config.get("output_folder"):
                cmd.extend(["-o", os.path.join(config["output_folder"], "%(title)s.%(ext)s")])

            cmd.append(url)

            if os.name == "nt":
                current_process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                current_process = subprocess.Popen(cmd)

            current_process.wait()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile avviare yt-dlp:\n{e}")
        finally:
            stop_loading_animation()

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
        f"Eseguibile: {config.get('exe_path') or '(non impostato)'}\n"
        f"Cartella output: {config.get('output_folder') or '(non impostata)'}"
    )
    messagebox.showinfo("Impostazioni correnti", info)

# --- Inizio UI ---
carica_impostazioni()

root = tk.Tk()
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

playlist_var = tk.BooleanVar(value=True)
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
