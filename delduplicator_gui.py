# /// script
# dependencies = []
# ///

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
# Uso intencional para ejecutar scripts locales controlados.
import subprocess  # nosec B404
import codecs
import threading
import sys
import os
import signal

APP_VERSION = "3.1.9"
GUI_SUBVERSION = "GUI.9"


class DelDuplicatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"DelDuplicator v{APP_VERSION} ({GUI_SUBVERSION}) - Interfaz Gráfica Pro")
        self.root.geometry("850x700")
        self.current_stage = "Estado: esperando..."
        self.current_file = ""
        
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

        self.lbl_action = ttk.Label(parent, text="Progreso de duplicados", foreground="#5fa9ff", anchor="w", justify="left")
        self.lbl_action.pack(fill="x", padx=20, pady=(4, 0))
        self.action_progress_bar = ttk.Progressbar(parent, orient="horizontal", mode="determinate")
        self.action_progress_bar.pack(fill="x", padx=20, pady=(0, 5))
        self.lbl_action_percent = ttk.Label(parent, text="0%")
        self.lbl_action_percent.pack()

        self.lbl_current_file = ttk.Label(parent, text="Estado: esperando...", foreground="#5fa9ff", anchor="w", justify="left")
        self.lbl_current_file.pack(fill="x", padx=20, pady=(0, 5))
        self.root.after(0, self._sync_status_wraplength)
        self.lbl_current_file.bind("<Configure>", self._sync_status_wraplength)

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

    def _safe_log_text(self, text):
        if text is None:
            return ""
        text = str(text)
        return text.encode("utf-8", "replace").decode("utf-8", "replace")

    def log(self, text):
        safe_text = self._safe_log_text(text)
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, safe_text + "\n")
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
        self.action_progress_bar['value'] = 0
        self.lbl_action_percent['text'] = "0%"
        self.current_stage = "Estado: iniciando..."
        self.current_file = ""
        self._refresh_status_label()

        threading.Thread(target=self.execute, args=(cmd,), daemon=True).start()

    def execute(self, cmd):
        try:
            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=False, bufsize=0,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )  # nosec B603

            tail = self._consume_process_output(self.current_process.stdout)
            if tail:
                self.root.after(0, self._process_output_fragment, tail)
            
            self.current_process.wait()
            self.current_process = None
            self.root.after(0, self.finish_process)
            
        except Exception as e:
            self.root.after(0, self.log, f"ERROR: {e}")
            self.current_process = None
            self.root.after(0, self.finish_process)

    def _consume_process_output(self, stdout_stream):
        decoder = codecs.getincrementaldecoder('utf-8')(errors='surrogateescape')
        buffer = ""

        while True:
            chunk = stdout_stream.read(1024)
            if not chunk:
                break

            buffer += decoder.decode(chunk)
            buffer = self._flush_output_fragments(buffer)

        buffer += decoder.decode(b"", final=True)
        return buffer.strip()

    def _flush_output_fragments(self, buffer):
        while True:
            cr_index = buffer.find("\r")
            nl_index = buffer.find("\n")

            if cr_index < 0 and nl_index < 0:
                return buffer

            if nl_index < 0 or (cr_index >= 0 and cr_index < nl_index):
                split_index = cr_index
            else:
                split_index = nl_index

            fragment = buffer[:split_index]
            buffer = buffer[split_index + 1:]
            self._process_output_fragment(fragment)

    def _process_output_fragment(self, fragment):
        line_clean = fragment.strip()
        if not line_clean:
            return

        line_clean = self._safe_log_text(line_clean)
        if line_clean.startswith(">> FASE 1:"):
            self.current_phase = "indexando"
            self.root.after(0, self.set_stage, "Indexando")
            return

        if line_clean.startswith(">> FASE 2:"):
            self.current_phase = "limpieza"
            self.root.after(0, self.set_stage, "Limpiando")
            self.root.after(0, self.update_progress, 20.0)
            self.root.after(0, self.update_action_progress, 0.0)
            return

        if line_clean.startswith(">> FASE 3:"):
            self.current_phase = "hash"
            self.root.after(0, self.set_stage, "Hashing")
            self.root.after(0, self.update_progress, 25.0)
            self.root.after(0, self.update_action_progress, 0.0)
            return

        if line_clean.startswith(">> FASE 4:"):
            self.current_phase = "duplicados"
            self.root.after(0, self.set_stage, "Analizando duplicados")
            self.root.after(0, self.update_progress, 85.0)
            self.root.after(0, self.update_action_progress, 0.0)
            return

        if line_clean.startswith("--- RESUMEN FINAL ---"):
            self.current_phase = "finalizando"
            self.root.after(0, self.set_stage, "Finalizando")
            self.root.after(0, self.update_progress, 100.0)
            self.root.after(0, self.update_action_progress, 100.0)
            return

        if line_clean.startswith("  Procesar:"):
            self.root.after(0, self.set_current_file, line_clean.split(":", 1)[1].strip())
            return

        if line_clean.startswith("Hashing: |"):
            self._handle_hashing_output(line_clean)
            return

        if line_clean.startswith("Duplicados: |"):
            self._handle_duplicate_output(line_clean)
            return

        self.root.after(0, self.log, line_clean)

    def _handle_hashing_output(self, line_clean):
        percent_value, suffix = self._parse_hashing_output(line_clean)
        if percent_value is not None:
            overall = 25.0 + (percent_value * 0.60)
            self.root.after(0, self.update_progress, overall)
            self.root.after(0, self.set_stage, "Hashing")

        action_value = self._extract_action_progress(suffix)
        if action_value is not None:
            self.root.after(0, self.update_action_progress, action_value)
        elif suffix == "Completado":
            self.root.after(0, self.update_action_progress, 100.0)
        if suffix:
            self.root.after(0, self.set_current_file, suffix)

    def _handle_duplicate_output(self, line_clean):
        percent_value, suffix = self._parse_hashing_output(line_clean)
        if percent_value is not None:
            overall = 85.0 + (percent_value * 0.15)
            self.root.after(0, self.update_progress, overall)
            self.root.after(0, self.set_stage, "Analizando duplicados")
            self.root.after(0, self.update_action_progress, percent_value)

        if suffix == "Completado":
            self.root.after(0, self.update_action_progress, 100.0)
        if suffix:
            self.root.after(0, self.set_current_file, suffix)

    def _parse_hashing_output(self, line_clean):
        bar_start = line_clean.find("|")
        if bar_start < 0:
            return None, None

        bar_end = line_clean.find("|", bar_start + 1)
        if bar_end < 0:
            return None, None

        remainder = line_clean[bar_end + 1 :].strip()
        if not remainder:
            return None, None

        parts = remainder.split(None, 1)
        if not parts:
            return None, None

        try:
            percent_value = float(parts[0].rstrip("%"))
        except ValueError:
            percent_value = None

        suffix = parts[1].strip() if len(parts) > 1 else ""
        return percent_value, suffix

    def _extract_action_progress(self, suffix):
        if not suffix:
            return None

        percent_marker = suffix.find("[")
        if percent_marker < 0:
            return None

        action_tail = suffix[percent_marker + 1 :]
        action_end = action_tail.find("%]")
        if action_end < 0:
            return None

        action_value_text = action_tail[:action_end].strip()
        try:
            return float(action_value_text)
        except ValueError:
            return None

    def update_progress(self, p):
        value = max(0.0, min(100.0, float(p)))
        self.progress_bar['value'] = value
        self.lbl_percent['text'] = f"{value:.1f}%"

    def update_action_progress(self, p):
        value = max(0.0, min(100.0, float(p)))
        self.action_progress_bar['value'] = value
        self.lbl_action_percent['text'] = f"{value:.1f}%"

    def set_current_file(self, current_file):
        self.current_file = self._safe_log_text(current_file)
        self._refresh_status_label()

    def set_stage(self, stage_name):
        self.current_stage = stage_name
        self._refresh_status_label()

    def _refresh_status_label(self):
        if self.current_file:
            self.lbl_current_file['text'] = f"{self.current_stage} | {self.current_file}"
        else:
            self.lbl_current_file['text'] = self.current_stage

    def _sync_status_wraplength(self, event=None):
        available_width = self.lbl_current_file.winfo_width()
        if available_width <= 1:
            available_width = max(self.progress_bar.winfo_width() - 8, 300)
        self.lbl_current_file.config(wraplength=max(available_width, 300))

    def finish_process(self):
        self.btn_run.config(state='normal')
        self.btn_restore.config(state='normal')
        self.btn_cancel.config(state='disabled')
        self.current_stage = "Estado: finalizado"
        self.current_file = ""
        self.update_progress(100.0)
        self.update_action_progress(100.0)
        self._refresh_status_label()
        self.log("--- FINALIZADO ---")
        messagebox.showinfo("Info", "Proceso completado.")

if __name__ == "__main__":
    root = tk.Tk()
    app = DelDuplicatorGUI(root)
    root.mainloop()
