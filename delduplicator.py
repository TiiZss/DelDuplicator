# /// script
# dependencies = []
# ///

import os
import hashlib
import sys
import shutil
import datetime
import sqlite3
import time
import platform
from pathlib import Path

# --- CONFIGURACIÓN DB ---
DEFAULT_DB_NAME = "delduplicator.db"

# --- LISTA NEGRA DE DIRECTORIOS (Seguridad) ---
SYSTEM_DIRS = {
    "Windows", "Program Files", "Program Files (x86)", 
    "System Volume Information", "$RECYCLE.BIN"
}
IGNORED_DIRS = {
    ".git", ".svn", ".venv", "node_modules", 
    "__pycache__", ".idea", ".vscode"
}

def init_db(db_path):
    """Inicializa la tabla de archivos si no existe."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            size INTEGER,
            mtime REAL,
            hash TEXT,
            last_seen REAL
        )
    ''')
    # Índices para acelerar búsquedas
    c.execute('CREATE INDEX IF NOT EXISTS idx_size ON files (size)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_hash ON files (hash)')
    conn.commit()
    return conn

def calcular_hash_sha256(ruta_archivo):
    """
    Calcula SHA-256 (Más seguro que MD5/SHA1).
    """
    sha256 = hashlib.sha256()
    bloque_size = 65536 
    
    try:
        with open(ruta_archivo, "rb") as f:
            while True:
                bloque = f.read(bloque_size)
                if not bloque:
                    break
                sha256.update(bloque)
        return sha256.hexdigest()
    except OSError:
        return None

def limpiar_log_obsoleto(log_path):
    """
    Lee el log de restauración y elimina las líneas de archivos 
    que ya no existen en el destino.
    """
    if not log_path.exists():
        return

    lineas_conservadas = []
    lineas_eliminadas = 0
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            contenido = f.readlines()
            
        for linea in contenido:
            partes = linea.strip().split(" | ")
            if len(partes) >= 3:
                ruta_destino = partes[2]
                if Path(ruta_destino).exists():
                    lineas_conservadas.append(linea)
                else:
                    lineas_eliminadas += 1
            else:
                lineas_conservadas.append(linea)
                
        if lineas_eliminadas > 0:
            with open(log_path, "w", encoding="utf-8") as f:
                f.writelines(lineas_conservadas)
            print(f"   [Log Cleanup] Se limpiaron {lineas_eliminadas} entradas obsoletas del log.")
            
    except Exception as e:
        print(f"   [Log Cleanup] Error: {e}")

def print_progress(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
    """
    Call in a loop to create terminal progress bar
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = '\r')
    # Print New Line on Complete
    if iteration == total: 
        print()

def escanear_y_eliminar(directorio, borrar_realmente, mover_a=None, includes=None, excludes=None, db_file=None):
    ruta_base = Path(directorio).resolve()
    if not ruta_base.exists():
        print(f"Error: El directorio '{ruta_base}' no existe.")
        return
        
    db_path = db_file if db_file else str(ruta_base / DEFAULT_DB_NAME)
    print(f"--- Base de Datos: {db_path} ---")

    # Configuración de modo
    acciones = []
    if borrar_realmente: acciones.append("BORRADO PERMANENTE")
    if mover_a: acciones.append(f"MOVER A '{mover_a}'")
    
    modo_txt = " + ".join(acciones) if acciones else "MODO SIMULACIÓN (DRY RUN)"
    if not acciones: modo_txt += " (No se harán cambios)"

    print(f"--- {modo_txt} ---")
    print(f"--- Escaneando: {ruta_base} ---\n")
    
    # Preparar ruta destino segura para evitar bucles (Si movemos a D:\Backup dentro de D:\)
    path_mover_abs = Path(mover_a).resolve() if mover_a else None
    
    # Filtros
    inc_exts = set(ext.lower() for ext in includes) if includes else None
    exc_exts = set(ext.lower() for ext in excludes) if excludes else None
    
    conn = init_db(db_path)
    cursor = conn.cursor()
    
    contador_duplicados = 0
    espacio_liberado = 0
    
    try:
        # --- FASE 1: INDEXACIÓN ---
        print(">> FASE 1: Indexando archivos (Actualizando DB)...")
        script_path = Path(__file__).resolve()
        scan_time = time.time()
        count_scanned = 0
        BATCH_SIZE = 1000
        
        # Preparamos queries
        sql_select = "SELECT size, mtime, hash FROM files WHERE path = ?"
        sql_insert = "INSERT INTO files (path, size, mtime, hash, last_seen) VALUES (?, ?, ?, ?, ?)"
        sql_update = "UPDATE files SET size=?, mtime=?, hash=?, last_seen=? WHERE path=?"
        sql_touch  = "UPDATE files SET last_seen=? WHERE path=?"

        for archivo_actual in ruta_base.rglob("*"):
            if not archivo_actual.is_file() or archivo_actual.is_symlink():
                continue
            
            # --- PROTECCIONES DE SEGURIDAD ---
            
            # 1. Protección propia y DB
            resolved_path = archivo_actual.resolve()
            if resolved_path == script_path: continue
            if str(resolved_path) == str(Path(db_path).resolve()): continue
            
            # 2. Ignorar carpeta destino de movimientos (Evitar Loop Infinito)
            if path_mover_abs and path_mover_abs in resolved_path.parents:
                continue

            # 3. Ignorar carpetas de sistema/ocultas
            parts = resolved_path.parts
            if any(p in SYSTEM_DIRS or p in IGNORED_DIRS for p in parts):
                continue
                
            # 4. Ignorar archivos de 0 bytes (Ruido)
            try:
                stat = archivo_actual.stat()
                if stat.st_size == 0:
                    continue
                
                # 5. Detección de Hardlinks (st_nlink > 1)
                # Si tiene más de 1 link, es el mismo fichero físico. No tocar.
                if hasattr(stat, 'st_nlink') and stat.st_nlink > 1:
                    continue
                    
                size = stat.st_size
                mtime = stat.st_mtime
                path_str = str(resolved_path)
                
                # ... (resto de indexación)
                
                # Check DB
                cursor.execute(sql_select, (path_str,))
                row = cursor.fetchone()
                
                if row:
                    # Existe. Verificar mtime/size
                    db_size, db_mtime, db_hash = row
                    if size != db_size or abs(mtime - db_mtime) > 0.001:
                        # Ha cambiado: Invalida hash
                        cursor.execute(sql_update, (size, mtime, None, scan_time, path_str))
                    else:
                        # No ha cambiado: Solo actualiza last_seen
                        cursor.execute(sql_touch, (scan_time, path_str))
                else:
                    # Nuevo
                    cursor.execute(sql_insert, (path_str, size, mtime, None, scan_time))
                
                count_scanned += 1
                if count_scanned % BATCH_SIZE == 0:
                    conn.commit()
                    print(f"   ... procesados {count_scanned} archivos", end='\r')
                    
            except OSError:
                continue

        conn.commit()
        print(f"   -> Total escaneados: {count_scanned}")
        
        # --- FASE 2: LIMPIEZA (PRUNE) ---
        print(">> FASE 2: Limpiando entradas obsoletas...")
        cursor.execute("DELETE FROM files WHERE last_seen < ?", (scan_time,))
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"   -> Eliminados {deleted_count} registros de archivos que ya no existen.")

        # --- FASE 3: CALCULO DE HASH (LAZY) ---
        print(">> FASE 3: Calculando hashes (solo colisiones de tamaño)...")
        # Buscar tamaños repetidos
        cursor.execute("SELECT count(*) FROM files WHERE hash IS NULL AND size IN (SELECT size FROM files GROUP BY size HAVING count(*) > 1)")
        row_count = cursor.fetchone()
        total_to_hash = row_count[0] if row_count else 0
        
        hashes_calculated = 0
        if total_to_hash > 0:
            print(f"   -> Necesario calcular hash de {total_to_hash} archivos candidatos...")
            
            # Iterar usando cursor server-side
            # SQLite puede bloquearse si leemos y escribimos al mismo tiempo con distintos cursores/conexiones
            # Solución: Leer por lotes en memoria (lista), cerrar cursor de lectura y procesar.
            
            offset = 0
            while True:
                # Leemos un lote de candidatos a procesar
                # Necesitamos nueva query cada vez porque estamos modificando la tabla (rellenando hash)
                # O usamos LIMIT/OFFSET
                cursor.execute(f"SELECT path FROM files WHERE hash IS NULL AND size IN (SELECT size FROM files GROUP BY size HAVING count(*) > 1) LIMIT 100")
                batch = cursor.fetchall()
                
                if not batch:
                    break
                    
                for path_tuple in batch:
                    path_str = path_tuple[0]
                    # GUI
                    fname = os.path.basename(path_str)
                    if len(fname) > 20: fname = fname[:17] + "..."
                    print_progress(hashes_calculated, total_to_hash, prefix='Hashing:', suffix=f'{fname}', length=30)
                    
                    # Usamos SHA256 ahora
                    sha256_val = calcular_hash_sha256(path_str)
                    if sha256_val:
                        final_hash = sha256_val
                        cursor.execute("UPDATE files SET hash=? WHERE path=?", (final_hash, path_str))
                    
                    hashes_calculated += 1
                
                # Commit por lote
                conn.commit()
            
            print_progress(total_to_hash, total_to_hash, prefix='Hashing:', suffix='Completado', length=30)
            print() # Salto final

            
        print(f"   -> Hashes nuevos calculados: {hashes_calculated}")

        # --- FASE 4: DEDUPLICACIÓN ---
        print(">> FASE 4: Analizando duplicados...")
        
        cursor.execute("SELECT hash, count(*) as cnt FROM files WHERE hash IS NOT NULL GROUP BY hash HAVING cnt > 1")
        duplicate_blocks = cursor.fetchall()
        
        # contador_duplicados = 0 # Ya inicializado arriba
        # espacio_liberado = 0
        
        for (file_hash, count) in duplicate_blocks:
            cursor.execute("SELECT path, mtime, size FROM files WHERE hash = ?", (file_hash,))
            candidates = []
            for row in cursor.fetchall():
                p_str, m_time, f_size = row
                candidates.append({
                    'path': Path(p_str),
                    'mtime': m_time,
                    'size': f_size
                })
            
            # Ordenar candidatos para decidir cual borrar
            # Queremos encontrar el "MEJOR" para conservar y borrar el resto
            # En nuestro loop original, comparabamos parejas. Aquí tenemos N archivos.
            # Convertimos a la lógica de "Elegir 1 KEEP, borrar N-1"
            
            match_copy_regex = re.compile(r' \(\d+\)$')
            
            # Estrategia: Buscar el "Mejor Candidato" para KEEP
            # Criterios para NO ser elegido (penalización):
            # 1. Tiene patrón " (1)" -> penalizado
            # 2. Es más nuevo -> penalizado
            
            # Ordenamos: 
            #  Prioridad 1: Que sea el script propio (seguridad extrema, aunque ya filtramos arriba)
            #  Prioridad 2: NO tiene patrón de copia (False < True)
            #  Prioridad 3: Más antiguo (menor mtime)
            
            # Nota sobre sort: Python sort es estable.
            # Queremos que el index 0 sea el que SE QUEDA.
            
            script_abs = script_path
            
            def sort_key(item):
                p = item['path']
                is_script = (p.resolve() == script_abs)
                has_copy_pattern = bool(match_copy_regex.search(p.stem))
                mtime = item['mtime']
                 
                # Tuple comparison:
                # 1. Is script? (True should come first -> invert boolean for sort?) 
                # We want "Best to Keep" at index 0.
                # Script: Priority #1. If is_script, key should be minimal. -> 0 else 1
                prio_script = 0 if is_script else 1
                
                # Pattern: Prefer clean (False) over copy (True). False=0, True=1.
                prio_pattern = 1 if has_copy_pattern else 0
                
                # Date: Prefer older (smaller mtime).
                return (prio_script, prio_pattern, mtime)
            
            candidates.sort(key=sort_key)
            
            keeper = candidates[0]
            to_delete = candidates[1:]
            
            print(f"[GRUPO DUPLICADO (x{len(candidates)})]")
            print(f"  Conservar: {keeper['path'].name}")
            
            for item in to_delete:
                archivo_delete = item['path']
                print(f"  Procesar:  {archivo_delete.name}")
                
                accion_exitosa = False
                
                # --- BORRAR DB ---
                # Si lo borramos del disco, lo quitamos de la DB para que no salga en next run
                # Si fallamos, lo dejamos.
                
                if mover_a:
                    try:
                        destino = Path(mover_a).resolve()
                        destino.mkdir(parents=True, exist_ok=True)
                        dest_f = destino / archivo_delete.name
                        
                        if dest_f.exists():
                             base = dest_f.stem
                             ext = dest_f.suffix
                             dest_f = destino / f"{base}_COPY_{file_hash[:8]}{ext}"
                        
                        shutil.move(str(archivo_delete), str(dest_f))
                        print(f"  Acción:    MOVIDO a {dest_f} ✅")
                        
                        # Log
                        log_file = destino / "restore_log.txt"
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        try:
                            with open(log_file, "a", encoding="utf-8") as f:
                                f.write(f"{timestamp} | {archivo_delete} | {dest_f}\n")
                        except: pass
                            
                        accion_exitosa = True
                    except Exception as e:
                        print(f"  Acción:    ERROR AL MOVER ({e}) ❌")
                        
                elif borrar_realmente:
                    try:
                        os.remove(archivo_delete)
                        print("  Acción:    ELIMINADO ✅")
                        accion_exitosa = True
                    except OSError as e:
                        print(f"  Acción:    ERROR BORRADO ({e}) ❌")
                else:
                    print("  Acción:    Se procesaría (Simulación) ⚠️")
                
                if accion_exitosa:
                    # Eliminar de la DB
                    cursor.execute("DELETE FROM files WHERE path=?", (str(archivo_delete),))
                    contador_duplicados += 1
                    espacio_liberado += item['size']
                
            print("-" * 40)
            conn.commit() # Commit tras cada grupo procesado

    except KeyboardInterrupt:
        print("\n\n!!! Interrumpido por usuario. Cerrando DB segura...")
    finally:
        conn.commit()
        conn.close()

    # Resumen
    print("\n--- RESUMEN FINAL ---")
    print(f"Estado: {modo_txt}")
    print(f"Duplicados procesados: {contador_duplicados}")
    print(f"Espacio (potencial):   {espacio_liberado / (1024 * 1024):.2f} MB")
    
    if mover_a:
        log_path = Path(mover_a).resolve() / "restore_log.txt"
        limpiar_log_obsoleto(log_path)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    parser = argparse.ArgumentParser(
        description="Script PRO (SQLite) para eliminar duplicados masivos.",
        epilog=r"""
---------------------------------------------------------------------
CARACTERÍSTICAS SQLITE:
- Se crea un archivo 'delduplicator.db' en la carpeta escaneada.
- Las ejecuciones sucesivas son INCREMENTALES (muy rápidas).
- Seguro para interrupciones (Ctrl+C).

EJEMPLOS:
1. Indexar y simular:
   python delduplicator.py "D:\Data"

2. Mover duplicados usando DB personalizada:
   python delduplicator.py . --mover "D:\Trash" --db-file "mi_indice.db"
---------------------------------------------------------------------
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("directorio", nargs="?", default=".", help="Directorio a escanear")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--borrar", action="store_true", help="BORRA los archivos duplicados.")
    group.add_argument("--mover", metavar="CARPETA", help="MUEVE duplicados a carpeta.")
    
    parser.add_argument("--include", nargs="+", help="Extensiones a INCLUIR")
    parser.add_argument("--exclude", nargs="+", help="Extensiones a EXCLUIR")
    
    parser.add_argument("--db-file", help="Ruta archivo DB (Opcional)")
    
    args = parser.parse_args()
    
    escanear_y_eliminar(
        args.directorio, 
        args.borrar, 
        mover_a=args.mover, 
        includes=args.include, 
        excludes=args.exclude,
        db_file=args.db_file
    )