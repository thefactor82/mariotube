import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import json

# Percorso file configurazione
config_file = os.path.join(os.path.expanduser("~"), ".mariotube")

# Variabili globali
config = {
    "exe_path": ""
}

def load_config():
    """Carica la configurazione da file"""
    global config
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            messagebox.showwarning("Errore", "Impossibile leggere il file di configurazione. Verrà ricreato.")

def save_config():
    """Salva la configurazione su file"""
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile salvare la configurazione:\n{e}")

def set_executable():
    """Seleziona l'eseguibile yt-dlp.exe"""
    file_path = filedialog.askopenfilename(
        title="Seleziona yt-dlp.exe",
        filetypes=[("yt-dlp", "yt-dlp.exe")],
    )
    if file_path:
        config["exe_path"] = file_path
        save_config()
        messagebox.showinfo("Impostazioni salvate", f"Eseguibile impostato:\n{file_path}")

def run_program():
    """Esegue il programma con il parametro"""
    if not config.get("exe_path"):
        messagebox.showwarning("Eseguibile mancante", "Prima imposta il percorso dell'eseguibile dalle impostazioni.")
        return
    param = entry.get().strip()
    if not param:
        messagebox.showwarning("Parametro mancante", "Inserisci un parametro prima di continuare.")
        return
    try:
        subprocess.Popen([config["exe_path"], param])
        messagebox.showinfo("Esecuzione", f"Avviato:\n{config['exe_path']} {param}")
    except Exception as e:
        messagebox.showerror("Errore", f"Non riesco ad avviare il programma.\nDettagli: {e}")

# Carica configurazione all'avvio
load_config()

# Creazione finestra principale
root = tk.Tk()
root.title("MarioTube Launcher")
root.geometry("400x180")

# Menu
menubar = tk.Menu(root)
settings_menu = tk.Menu(menubar, tearoff=0)
settings_menu.add_command(label="Imposta eseguibile", command=set_executable)
menubar.add_cascade(label="Impostazioni", menu=settings_menu)
root.config(menu=menubar)

# Etichetta
label = tk.Label(root, text="Inserisci il parametro:")
label.pack(pady=10)

# Campo testo
entry = tk.Entry(root, width=50)
entry.pack(pady=5)

# Pulsante GO
button = tk.Button(root, text="GO", command=run_program, bg="green", fg="white", font=("Arial", 12, "bold"))
button.pack(pady=10)

# Avvio interfaccia
root.mainloop()
