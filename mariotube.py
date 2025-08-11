import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import json

# Percorsi file
config_file = os.path.join(os.path.expanduser("~"), ".mariotube")
pid_file = os.path.join(os.path.expanduser("~"), ".mariotube.pid")

# Config iniziale
config = {"exe_path": ""}
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

    try:
        # Su Windows possiamo creare un new process group (opzionale)
        if os.name == "nt":
            current_process = subprocess.Popen([config["exe_path"], param],
                                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            current_process = subprocess.Popen([config["exe_path"], param])

        # Salvo il pid su file così anche un'altra istanza del launcher può trovarlo
        try:
            with open(pid_file, "w", encoding="utf-8") as f:
                f.write(str(current_process.pid))
        except Exception:
            pass

        messagebox.showinfo("Esecuzione", f"Avviato:\n{config['exe_path']} {param}\nPID: {current_process.pid}")
        update_buttons()
    except Exception as e:
        messagebox.showerror("Errore", f"Non riesco ad avviare il programma.\nDettagli: {e}")

def stop_program():
    """Termina il processo (preferibilmente l'albero di processi)."""
    global current_process
    pid = None

    # Prima preferiamo il processo corrente se ancora attivo
    if current_process and current_process.poll() is None:
        pid = current_process.pid
    else:
        # Proviamo a leggere il pid salvato su file (se esiste)
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
            # Uso taskkill per Windows: forza (/F) e termina albero (/T)
            res = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                                 capture_output=True, text=True)
            if res.returncode == 0:
                messagebox.showinfo("STOP", f"Processo {pid} terminato con successo.")
            else:
                # Se taskkill fallisce (es. PID non esiste), offro di killare per nome
                ask = messagebox.askyesno("Processo non trovato",
                                          f"Non sono riuscito a terminare il PID {pid} (potrebbe non esistere).\n"
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
            # taskkill non trovato (non-Windows) -> fallback su terminate()
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
        # Nessun pid noto: offriamo di killare per nome (potrebbe essere l'unica opzione)
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

    # Pulizia
    current_process = None
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    except Exception:
        pass

    update_buttons()

def update_buttons():
    """Abilita/disabilita GO/STOP in base allo stato del processo."""
    running = False
    if current_process and current_process.poll() is None:
        running = True

    button_go.config(state="normal" if not running else "disabled")
    button_stop.config(state="normal" if running else "disabled")

    # richiamo periodico
    root.after(500, update_buttons)

# Carica configurazione e costruisci UI
load_config()

root = tk.Tk()
root.title("MarioTube Launcher")
root.geometry("480x180")

menubar = tk.Menu(root)
settings_menu = tk.Menu(menubar, tearoff=0)
settings_menu.add_command(label="Imposta eseguibile", command=set_executable)
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

# Avvio loop di update bottoni
update_buttons()

root.mainloop()
