import subprocess
import tkinter as tk
from tkinter import messagebox

# Percorso del programma da eseguire
exe_path = r"C:\Users\mmatteis\Downloads\yt-dlp.exe --no-playlist"

def run_program():
    param = entry.get().strip()
    if not param:
        messagebox.showwarning("Parametro mancante", "Inserisci un parametro prima di continuare.")
        return
    try:
        subprocess.Popen([exe_path, param])
        messagebox.showinfo("Esecuzione", f"Avviato:\n{exe_path} {param}")
    except Exception as e:
        messagebox.showerror("Errore", f"Non riesco ad avviare il programma.\nDettagli: {e}")

# Creazione finestra
root = tk.Tk()
root.title("Launcher")
root.geometry("400x150")

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
