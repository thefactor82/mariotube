import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import json

# Percorsi file
config_file = os.path.join(os.path.expanduser("~"), ".mariotube")
pid_file = os.path.join(os.path.expanduser("~"), ".mariotube.pid")

# Config iniziale
config = {
    "exe_path": "",
    "output_dir": ""
}
current_process = None

def load_config():
    global config
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            messagebox.showwarning("Errore", "Impossibile leggere il file di configurazione. Verrà ricreato.")

def save_config():
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile salvare la configurazione:\n{e}")

def set_executable():
    file_path = filedialog.askopenfilename(
        title="Seleziona yt-dlp.exe",
        filetypes=[("yt-dlp", "yt-dlp.exe")],
    )
    if file_path:
        config["exe_path"] = file_path
        save_config()
        messagebox.showinfo("Impostazioni salvate", f"Eseguibile impostato:\n{file_path}")

def set_output_dir():
    folder_path = filedialog.askdirectory(
        title="Seleziona cartella di output"
    )
    if folder_path:
        config["output_dir"] = folder_path
        save_config()
        messagebox.showinfo("Impostazioni salvate", f"Cartella di output impostata:\n{folder_path}")

def show_settings():
    exe_info = config.get("exe_path", "") or "(non impostato)"
    out_info = config.get("output_dir", "") or "(non impostata)"
    msg = f"Eseguibile:\n{exe_info}\n\nCartella di output:\n{out_info}"
    messagebox.showinfo("Impostazioni attuali", msg)

def run_program():
    """Avvia yt-dlp con il parametro e salva il PID su file."""
    global current_process
    if not config.get("exe_path"):
        messagebox.showwarning("Eseguibile mancante", "Prima imposta il percorso dell'eseguibile dalle impostazioni.")
        return
    param = entry.get().strip()
    if not param:
        messagebox.showwarning("Parametro mancante", "Inserisci un parametro prima di continuare.")
        return

    cmd = [config["exe_path"]]

    # Se cartella di output impostata, aggiungo l'opzione -o
    if config.get("output_dir"):
        output_template = os.path.join(config["output_dir"], "%(title)s.%(ext)s")
        cmd.extend(["-o", output_template])

    cmd.append(param)

    try:
        if os.name == "nt":
            current_process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            current_process = subprocess.Popen(cmd)

        with open(pid_file, "w", encoding="utf-8") as f:
            f.write(str(current_process.pid))

        messagebox.showinfo("Esecuzione", f"Avviato:\n{' '.join(cmd)}\nPID: {current_process.pid}")
        update_buttons()
    except Exception as e:
        messagebox.showerror("Errore", f"Non riesco ad avviare il programma.\nDettagli: {e}")

def stop_program():
    global current_process
    pid = None
    if current_process and current_process.poll() is None:
        pid = current_process.pid
    elif os.path.exists(pid_file):
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
                                          f"PID {pid} non trovato.\nVuoi terminare tutti i processi 'yt-dlp.exe'?")
                if ask:
                    subprocess.run(["taskkill", "/F", "/IM", "yt-dlp.exe", "/T"])
        except FileNotFoundError:
            if current_process and current_process.poll() is None:
                current_process.terminate()
                current_process.wait(timeout=5)
                messagebox.showinfo("STOP", "Processo terminato.")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la terminazione:\n{e}")
    else:
        ask_all = messagebox.askyesno("Nessun processo noto",
                                      "Vuoi terminare tutti i processi 'yt-dlp.exe' attivi?")
        if ask_all:
            subprocess.run(["taskkill", "/F", "/IM", "yt-dlp.exe", "/T"])

    current_process = None
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    except Exception:
        pass

    update_buttons()

def update_buttons():
    running = current_process and current_process.poll() is None
    button_go.config(state="normal" if not running else "disabled")
    button_stop.config(state="normal" if running else "disabled")
    root.after(500, update_buttons)

# Avvio
load_config()

root = tk.Tk()
root.title("MarioTube Launcher")
root.geometry("500x200")

menubar = tk.Menu(root)
settings_menu = tk.Menu(menubar, tearoff=0)
settings_menu.add_command(label="Imposta eseguibile", command=set_executable)
settings_menu.add_command(label="Imposta cartella di output", command=set_output_dir)
settings_menu.add_separator()
settings_menu.add_command(label="Visualizza impostazioni attuali", command=show_settings)
menubar.add_cascade(label="Impostazioni", menu=settings_menu)
root.config(menu=menubar)

label = tk.Label(root, text="Inserisci il parametro:")
label.pack(pady=10)

entry = tk.Entry(root, width=60)
entry.pack(pady=5)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

button_go = tk.Button(button_frame, text="GO", command=run_program,
                      bg="green", fg="white", font=("Arial", 12, "bold"))
button_go.pack(side="left", padx=5)

button_stop = tk.Button(button_frame, text="STOP", command=stop_program,
                        bg="red", fg="white", font=("Arial", 12, "bold"))
button_stop.pack(side="left", padx=5)

update_buttons()
root.mainloop()
