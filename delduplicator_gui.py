# /// script
# dependencies = []
# ///

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import sys
import os
import re
import signal

class DelDuplicatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DelDuplicator V3 - Interfaz Gráfica Pro")
        self.root.geometry("850x700")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # --- SISTEMA DE PESTAÑAS ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Pestaña 1: Escáner
        self.tab_scan = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_scan, text="🛡️ Escanear y Limpiar")
        self.init_scan_tab(self.tab_scan)
        
        # Pestaña 2: Restaurar
        self.tab_restore = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_restore, text="🚑 Restaurar (Deshacer)")
        self.init_restore_tab(self.tab_restore)
        
        # --- ÁREA COMÚN DE LOGS ---
        frame_log = ttk.LabelFrame(root, text=" Salida del Proceso ", padding=5)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(frame_log, state='disabled', height=10, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        self.current_process = None

    def init_scan_tab(self, parent):
        # 1. Directorio
        frame_dir = ttk.LabelFrame(parent, text=" 1. Directorio a Escanear ", padding=10)
        frame_dir.pack(fill="x", padx=10, pady=5)
        
        self.dir_path = tk.StringVar()
        ttk.Entry(frame_dir, textvariable=self.dir_path).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(frame_dir, text="Examinar...", command=lambda: self.browse_dir(self.dir_path)).pack(side="left")
        
        # 2. Config
        frame_config = ttk.LabelFrame(parent, text=" 2. Configuración ", padding=10)
        frame_config.pack(fill="x", padx=10, pady=5)
        
        # Modo
        ttk.Label(frame_config, text="Acción:").grid(row=0, column=0, sticky="w", pady=5)
        self.action_var = tk.StringVar(value="dryrun")
        ttk.Radiobutton(frame_config, text="Simulación", variable=self.action_var, value="dryrun", command=self.toggle_move_entry).grid(row=0, column=1)
        ttk.Radiobutton(frame_config, text="Mover (Seguro)", variable=self.action_var, value="move", command=self.toggle_move_entry).grid(row=0, column=2)
        ttk.Radiobutton(frame_config, text="Borrar (Peligro)", variable=self.action_var, value="delete", command=self.toggle_move_entry).grid(row=0, column=3)
        
        # Move Path
        ttk.Label(frame_config, text="Carpeta Destino:").grid(row=1, column=0, sticky="w", pady=5)
        self.move_path = tk.StringVar()
        self.entry_move = ttk.Entry(frame_config, textvariable=self.move_path)
        self.entry_move.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5)
        self.btn_move_browse = ttk.Button(frame_config, text="Examinar...", command=lambda: self.browse_dir(self.move_path))
        self.btn_move_browse.grid(row=1, column=3, sticky="w")
        
        # Filtros
        ttk.Label(frame_config, text="Incluir Ext:").grid(row=2, column=0, sticky="w")
        self.include_ext = tk.StringVar()
        ttk.Entry(frame_config, textvariable=self.include_ext).grid(row=2, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        
        ttk.Label(frame_config, text="Excluir Ext:").grid(row=3, column=0, sticky="w")
        self.exclude_ext = tk.StringVar()
        ttk.Entry(frame_config, textvariable=self.exclude_ext).grid(row=3, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        
        # Botones Acción
        frame_btns = ttk.Frame(parent, padding=10)
        frame_btns.pack(fill="x", padx=10)
        
        self.btn_run = ttk.Button(frame_btns, text="EJECUTAR ANÁLISIS/LIMPIEZA", command=self.run_process_scan)
        self.btn_run.pack(side="left", fill="x", expand=True, ipady=5, padx=5)
        
        self.btn_cancel = ttk.Button(frame_btns, text="CANCELAR", command=self.cancel_process, state="disabled")
        self.btn_cancel.pack(side="right", ipady=5, padx=5)
        
        # Progreso
        self.progress_bar = ttk.Progressbar(parent, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=20, pady=5)
        self.lbl_percent = ttk.Label(parent, text="0%")
        self.lbl_percent.pack()
        
        self.toggle_move_entry()

    def init_restore_tab(self, parent):
        frame_top = ttk.LabelFrame(parent, text=" Archivo de Log ", padding=10)
        frame_top.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(frame_top, text="Selecciona el archivo 'restore_log.txt':").pack(anchor="w")
        
        frame_sel = ttk.Frame(frame_top)
        frame_sel.pack(fill="x", pady=5)
        
        self.log_path_var = tk.StringVar()
        ttk.Entry(frame_sel, textvariable=self.log_path_var).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(frame_sel, text="Buscar log...", command=self.browse_log).pack(side="left")
        
        self.btn_restore = ttk.Button(parent, text="INICIAR RESTAURACIÓN (DESHACER)", command=self.run_process_restore)
        self.btn_restore.pack(fill="x", padx=20, pady=20, ipady=10)

    # --- COMUNES ---
    def browse_dir(self, var):
        d = filedialog.askdirectory()
        if d: var.set(d)
    
    def browse_log(self):
        f = filedialog.askopenfilename(filetypes=[("Log Files", "*.txt"), ("All Files", "*.*")])
        if f: self.log_path_var.set(f)
        
    def toggle_move_entry(self):
        if self.action_var.get() == "move":
            self.entry_move.config(state='normal')
            self.btn_move_browse.config(state='normal')
        else:
            self.entry_move.config(state='disabled')
            self.btn_move_browse.config(state='disabled')

    def log(self, text):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
    def cancel_process(self):
        if self.current_process:
            self.log("!!! INTENTANDO CANCELAR PROCESO...")
            # En Windows subprocess.terminate() a veces no mata hijos, pero python -u ayuda.
            self.current_process.terminate()

    # --- EJECUCIÓN ---
    def run_process_scan(self):
        target = self.dir_path.get()
        if not target: return messagebox.showerror("Error", "Falta directorio.")
        
        cmd = [sys.executable, "-u", "delduplicator.py", target]
        
        if self.action_var.get() == "move":
            dest = self.move_path.get()
            if not dest: return messagebox.showerror("Error", "Falta destino mover.")
            cmd.extend(["--mover", dest])
        elif self.action_var.get() == "delete":
            if not messagebox.askyesno("Confirmar", "Vas a borrar permanentemente. ¿Seguro?"): return
            cmd.append("--borrar")
            
        if self.include_ext.get().strip():
            cmd.append("--include")
            cmd.extend(self.include_ext.get().split())
        
        if self.exclude_ext.get().strip():
            cmd.append("--exclude")
            cmd.extend(self.exclude_ext.get().split())
            
        self.start_thread(cmd)

    def run_process_restore(self):
        logf = self.log_path_var.get()
        if not logf or not os.path.exists(logf):
            return messagebox.showerror("Error", "Archivo log inválido.")
            
        cmd = [sys.executable, "-u", "restore.py", logf]
        self.start_thread(cmd)

    def start_thread(self, cmd):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        
        self.btn_run.config(state='disabled')
        self.btn_restore.config(state='disabled')
        self.btn_cancel.config(state='normal')
        self.progress_bar['value'] = 0
        self.lbl_percent['text'] = "0%"
        
        threading.Thread(target=self.execute, args=(cmd,), daemon=True).start()

    def execute(self, cmd):
        try:
            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                text=True, bufsize=1, encoding='utf-8', errors='replace',
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            regex_progress = re.compile(r"\|.*\| (\d+\.?\d*)%")
            
            for line in self.current_process.stdout:
                line_clean = line.strip()
                if "Hashing: |" in line_clean:
                    match = regex_progress.search(line_clean)
                    if match:
                        p = float(match.group(1))
                        self.root.after(0, self.update_progress, p)
                else:
                    self.root.after(0, self.log, line_clean)
            
            self.current_process.wait()
            self.current_process = None
            self.root.after(0, self.finish_process)
            
        except Exception as e:
            self.root.after(0, self.log, f"ERROR: {e}")
            self.current_process = None
            self.root.after(0, self.finish_process)

    def update_progress(self, p):
        self.progress_bar['value'] = p
        self.lbl_percent['text'] = f"{p:.1f}%"

    def finish_process(self):
        self.btn_run.config(state='normal')
        self.btn_restore.config(state='normal')
        self.btn_cancel.config(state='disabled')
        self.log("--- FINALIZADO ---")
        messagebox.showinfo("Info", "Proceso completado.")

if __name__ == "__main__":
    root = tk.Tk()
    app = DelDuplicatorGUI(root)
    root.mainloop()
