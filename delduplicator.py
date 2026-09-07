# /// script
# dependencies = []
# ///

import os
import hashlib
import sys
import argparse
import re
import shutil
import datetime
import sqlite3
import time
import platform
from pathlib import Path

try:
    import xxhash
except ImportError:
    xxhash = None

# --- CONFIGURACIÓN DB ---
DEFAULT_DB_NAME = "delduplicator.db"
QUICK_SAMPLE_BYTES = 4096

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
            hash BLOB,
            hash_error INTEGER DEFAULT 0,
            last_seen REAL
        )
    ''')
    # Migración ligera para bases previas (hash TEXT sin hash_error).
    c.execute("PRAGMA table_info(files)")
    cols = {row[1] for row in c.fetchall()}
    if "hash_error" not in cols:
        c.execute("ALTER TABLE files ADD COLUMN hash_error INTEGER DEFAULT 0")

    # Si hay hashes en texto de versiones previas, forzamos recálculo binario.
    c.execute("UPDATE files SET hash = NULL, hash_error = 0 WHERE typeof(hash) = 'text'")

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
        return sha256.digest()
    except OSError:
        return None


def calcular_firma_rapida(ruta_archivo):
    """
    Firma rápida de los primeros 4KB para filtrar antes del hash completo.
    """
    try:
        with open(ruta_archivo, "rb") as f:
            head = f.read(QUICK_SAMPLE_BYTES)
    except OSError:
        return None

    if xxhash is not None:
        return xxhash.xxh3_128_digest(head)
    return hashlib.blake2b(head, digest_size=16).digest()


def calcular_hash_completo(ruta_archivo):
    """
    Hash completo en binario: XXH3-128 si está disponible, fallback SHA-256.
    """
    if xxhash is None:
        return calcular_hash_sha256(ruta_archivo)

    h = xxhash.xxh3_128()
    bloque_size = 65536
    try:
        with open(ruta_archivo, "rb") as f:
            while True:
                bloque = f.read(bloque_size)
                if not bloque:
                    break
                h.update(bloque)
    except OSError:
        return None
    return h.digest()

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


def _normalize_ext(ext):
    ext = ext.strip().lower()
    if not ext:
        return None
    return ext if ext.startswith('.') else f'.{ext}'


def _build_extension_filters(includes, excludes):
    include_exts = {_normalize_ext(ext) for ext in includes} if includes else None
    exclude_exts = {_normalize_ext(ext) for ext in excludes} if excludes else None
    if include_exts:
        include_exts.discard(None)
    if exclude_exts:
        exclude_exts.discard(None)
    return include_exts, exclude_exts


def _is_indexable_regular_file(archivo_actual):
    return archivo_actual.is_file() and not archivo_actual.is_symlink()


def _is_protected_path(resolved_path, script_path, db_resolved, path_mover_abs):
    if resolved_path == script_path:
        return True
    if resolved_path == db_resolved:
        return True
    if path_mover_abs and path_mover_abs in resolved_path.parents:
        return True
    parts = resolved_path.parts
    return any(p in SYSTEM_DIRS or p in IGNORED_DIRS for p in parts)


def _passes_file_property_filters(archivo_actual, stat, include_exts, exclude_exts):
    if stat.st_size == 0:
        return False
    if hasattr(stat, 'st_nlink') and stat.st_nlink > 1:
        return False

    file_ext = archivo_actual.suffix.lower()
    if include_exts is not None and file_ext not in include_exts:
        return False
    if exclude_exts is not None and file_ext in exclude_exts:
        return False
    return True


def _iter_eligible_files(ruta_base, script_path, db_path, path_mover_abs, include_exts, exclude_exts):
    db_resolved = Path(db_path).resolve()
    for archivo_actual in ruta_base.rglob("*"):
        if not _is_indexable_regular_file(archivo_actual):
            continue

        try:
            resolved_path = archivo_actual.resolve()
            stat = archivo_actual.stat()
        except OSError:
            continue

        if _is_protected_path(resolved_path, script_path, db_resolved, path_mover_abs):
            continue

        if not _passes_file_property_filters(archivo_actual, stat, include_exts, exclude_exts):
            continue

        yield resolved_path, stat


def _phase_index_files(conn, cursor, ruta_base, script_path, db_path, path_mover_abs, include_exts, exclude_exts):
    print(">> FASE 1: Indexando archivos (Actualizando DB)...")
    scan_time = time.time()
    count_scanned = 0
    batch_size = 1000

    sql_select = "SELECT size, mtime, hash FROM files WHERE path = ?"
    sql_insert = "INSERT INTO files (path, size, mtime, hash, hash_error, last_seen) VALUES (?, ?, ?, ?, ?, ?)"
    sql_update = "UPDATE files SET size=?, mtime=?, hash=?, hash_error=?, last_seen=? WHERE path=?"
    sql_touch = "UPDATE files SET last_seen=? WHERE path=?"

    for resolved_path, stat in _iter_eligible_files(
        ruta_base,
        script_path,
        db_path,
        path_mover_abs,
        include_exts,
        exclude_exts,
    ):
        size = stat.st_size
        mtime = stat.st_mtime
        path_str = str(resolved_path)

        cursor.execute(sql_select, (path_str,))
        row = cursor.fetchone()
        if row:
            db_size, db_mtime, _ = row
            if size != db_size or abs(mtime - db_mtime) > 0.001:
                cursor.execute(sql_update, (size, mtime, None, 0, scan_time, path_str))
            else:
                cursor.execute(sql_touch, (scan_time, path_str))
        else:
            cursor.execute(sql_insert, (path_str, size, mtime, None, 0, scan_time))

        count_scanned += 1
        if count_scanned % batch_size == 0:
            conn.commit()
            print(f"   ... procesados {count_scanned} archivos", end='\r')

    conn.commit()
    print(f"   -> Total escaneados: {count_scanned}")
    return scan_time


def _phase_prune_db(conn, cursor, scan_time):
    print(">> FASE 2: Limpiando entradas obsoletas...")
    cursor.execute("DELETE FROM files WHERE last_seen < ?", (scan_time,))
    deleted_count = cursor.rowcount
    conn.commit()
    print(f"   -> Eliminados {deleted_count} registros de archivos que ya no existen.")


def _phase_calculate_hashes(conn, cursor):
    print(">> FASE 3: Filtro por cabecera y hash en colisiones reales...")
    pending_predicate = "(hash IS NULL AND hash_error = 0)"

    cursor.execute(
        f"SELECT count(*) FROM files WHERE {pending_predicate} "
        "AND size IN (SELECT size FROM files GROUP BY size HAVING count(*) > 1)"
    )
    row_count = cursor.fetchone()
    total_candidates = row_count[0] if row_count else 0

    processed_candidates = 0
    hashes_calculated = 0

    if total_candidates <= 0:
        print(f"   -> Hashes completos calculados: {hashes_calculated}")
        return

    print(f"   -> Candidatos por tamaño: {total_candidates}")
    cursor.execute("SELECT size FROM files GROUP BY size HAVING count(*) > 1")
    duplicate_sizes = [row[0] for row in cursor.fetchall()]

    for file_size in duplicate_sizes:
        cursor.execute("SELECT path, hash, hash_error FROM files WHERE size = ?", (file_size,))
        size_group = cursor.fetchall()

        quick_groups = {}
        for path_str, _, _ in size_group:
            quick_sig = calcular_firma_rapida(path_str)
            if quick_sig is None:
                cursor.execute("UPDATE files SET hash=NULL, hash_error=1 WHERE path=?", (path_str,))
                continue

            quick_groups.setdefault(quick_sig, []).append(path_str)

        for quick_sig, group_files in quick_groups.items():
            pending_paths = []
            for path_str in group_files:
                cursor.execute("SELECT hash, hash_error FROM files WHERE path=?", (path_str,))
                row = cursor.fetchone()
                if row and row[0] is None and row[1] == 0:
                    pending_paths.append(path_str)

            if not pending_paths:
                continue

            if len(group_files) == 1:
                for path_str in pending_paths:
                    processed_candidates += 1
                    fname = os.path.basename(path_str)
                    if len(fname) > 20:
                        fname = fname[:17] + "..."
                    print_progress(processed_candidates, total_candidates, prefix='Hashing:', suffix=f'{fname}', length=30)
                continue

            for path_str in pending_paths:
                processed_candidates += 1
                fname = os.path.basename(path_str)
                if len(fname) > 20:
                    fname = fname[:17] + "..."
                print_progress(processed_candidates, total_candidates, prefix='Hashing:', suffix=f'{fname}', length=30)

                full_hash = calcular_hash_completo(path_str)
                if full_hash is None:
                    cursor.execute("UPDATE files SET hash=NULL, hash_error=1 WHERE path=?", (path_str,))
                else:
                    hashes_calculated += 1
                    cursor.execute("UPDATE files SET hash=?, hash_error=0 WHERE path=?", (full_hash, path_str))

        conn.commit()

    print_progress(total_candidates, total_candidates, prefix='Hashing:', suffix='Completado', length=30)
    print()
    print(f"   -> Hashes completos calculados: {hashes_calculated}")


def _hash_tag_for_filename(file_hash):
    if isinstance(file_hash, (bytes, bytearray, memoryview)):
        return bytes(file_hash).hex()[:8]
    return str(file_hash)[:8]


def _sort_duplicate_candidates(candidates, script_path):
    match_copy_regex = re.compile(r' \((\d+)\)$')

    def copy_index(path_obj, copy_regex=match_copy_regex):
        match = copy_regex.search(path_obj.stem)
        if not match:
            return None
        return int(match.group(1))

    def sort_key(item, script_abs=script_path, copy_regex=match_copy_regex):
        p = item['path']
        is_script = p.resolve() == script_abs
        idx = copy_index(p, copy_regex)
        has_copy_pattern = idx is not None
        mtime = item['mtime']
        prio_script = 0 if is_script else 1
        prio_pattern = 1 if has_copy_pattern else 0
        prio_copy_index = idx if idx is not None else float('inf')
        return (prio_script, prio_pattern, prio_copy_index, mtime)

    candidates.sort(key=sort_key)


def _move_or_delete_duplicate(mover_a, borrar_realmente, file_hash, archivo_delete):
    if mover_a:
        destino = Path(mover_a).resolve()
        destino.mkdir(parents=True, exist_ok=True)
        dest_f = destino / archivo_delete.name
        if dest_f.exists():
            base = dest_f.stem
            ext = dest_f.suffix
            hash_tag = _hash_tag_for_filename(file_hash)
            dest_f = destino / f"{base}_COPY_{hash_tag}{ext}"

        shutil.move(str(archivo_delete), str(dest_f))
        print(f"  Acción:    MOVIDO a {dest_f} ✅")

        log_file = destino / "restore_log.txt"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} | {archivo_delete} | {dest_f}\n")
        except OSError:
            # Si el log falla no detenemos el flujo principal de deduplicacion.
            pass
        return True

    if borrar_realmente:
        os.remove(archivo_delete)
        print("  Acción:    ELIMINADO ✅")
        return True

    print("  Acción:    Se procesaría (Simulación) ⚠️")
    return False


def _phase_deduplicate(conn, cursor, mover_a, borrar_realmente, script_path):
    print(">> FASE 4: Analizando duplicados...")
    cursor.execute(
        "SELECT hash, count(*) as cnt FROM files "
        "WHERE hash IS NOT NULL "
        "AND hash_error = 0 "
        "GROUP BY hash HAVING cnt > 1"
    )
    duplicate_blocks = cursor.fetchall()

    contador_duplicados = 0
    espacio_liberado = 0

    for (file_hash, _) in duplicate_blocks:
        cursor.execute("SELECT path, mtime, size FROM files WHERE hash = ?", (file_hash,))
        candidates = [
            {'path': Path(p_str), 'mtime': m_time, 'size': f_size}
            for (p_str, m_time, f_size) in cursor.fetchall()
        ]

        _sort_duplicate_candidates(candidates, script_path)
        keeper = candidates[0]
        to_delete = candidates[1:]

        print(f"[GRUPO DUPLICADO (x{len(candidates)})]")
        print(f"  Conservar: {keeper['path'].name}")

        for item in to_delete:
            archivo_delete = item['path']
            print(f"  Procesar:  {archivo_delete.name}")

            accion_exitosa = False
            try:
                accion_exitosa = _move_or_delete_duplicate(mover_a, borrar_realmente, file_hash, archivo_delete)
            except Exception as e:
                if mover_a:
                    print(f"  Acción:    ERROR AL MOVER ({e}) ❌")
                elif borrar_realmente:
                    print(f"  Acción:    ERROR BORRADO ({e}) ❌")

            if accion_exitosa:
                cursor.execute("DELETE FROM files WHERE path=?", (str(archivo_delete),))
                contador_duplicados += 1
                espacio_liberado += item['size']

        print("-" * 40)
        conn.commit()

    return contador_duplicados, espacio_liberado

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
    
    path_mover_abs = Path(mover_a).resolve() if mover_a else None
    include_exts, exclude_exts = _build_extension_filters(includes, excludes)

    conn = init_db(db_path)
    cursor = conn.cursor()
    
    contador_duplicados = 0
    espacio_liberado = 0
    
    try:
        script_path = Path(__file__).resolve()
        scan_time = _phase_index_files(
            conn,
            cursor,
            ruta_base,
            script_path,
            db_path,
            path_mover_abs,
            include_exts,
            exclude_exts,
        )
        _phase_prune_db(conn, cursor, scan_time)
        _phase_calculate_hashes(conn, cursor)
        contador_duplicados, espacio_liberado = _phase_deduplicate(
            conn,
            cursor,
            mover_a,
            borrar_realmente,
            script_path,
        )

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