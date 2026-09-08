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
INT64_MASK = (1 << 64) - 1
INT64_SIGN_BIT = 1 << 63
HASH_PROGRESS_PREFIX = "Hashing:"
DEDUP_PROGRESS_PREFIX = "Duplicados:"
FILE_COMPARE_CHUNK_SIZE = 65536

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

    # Si hay hashes legados (texto/integer), forzamos recálculo en formato 128 bits.
    c.execute("UPDATE files SET hash = NULL, hash_error = 0 WHERE hash IS NOT NULL AND typeof(hash) != 'blob'")

    # Índices para acelerar búsquedas
    c.execute('CREATE INDEX IF NOT EXISTS idx_size ON files (size)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_hash ON files (hash)')
    c.execute('''
        CREATE TABLE IF NOT EXISTS scan_state (
            root_path TEXT PRIMARY KEY,
            filters_key TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            updated_at REAL
        )
    ''')
    conn.commit()
    return conn


def _build_filters_key(include_exts, exclude_exts):
    include_key = ','.join(sorted(include_exts)) if include_exts else ''
    exclude_key = ','.join(sorted(exclude_exts)) if exclude_exts else ''
    return f'{include_key}|{exclude_key}'


def _get_directory_mtime(directory_path):
    try:
        return Path(directory_path).stat().st_mtime
    except OSError:
        return 0.0


def _load_scan_state(cursor, root_path, filters_key):
    cursor.execute(
        'SELECT filters_key, completed FROM scan_state WHERE root_path = ?',
        (str(root_path),)
    )
    row = cursor.fetchone()
    if not row:
        return None
    stored_filters_key, completed = row
    if stored_filters_key != filters_key:
        return None
    return {'completed': int(completed)}


def _save_scan_state(conn, cursor, root_path, filters_key, completed):
    cursor.execute(
        '''
        INSERT INTO scan_state (root_path, filters_key, completed, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(root_path) DO UPDATE SET
            filters_key = excluded.filters_key,
            completed = excluded.completed,
            updated_at = excluded.updated_at
        ''',
        (str(root_path), filters_key, 1 if completed else 0, time.time())
    )
    conn.commit()

def calcular_hash_sha256(ruta_archivo):
    """
    Calcula un fallback de 128 bits derivado de SHA-256.
    """
    sha256 = hashlib.sha256()
    bloque_size = FILE_COMPARE_CHUNK_SIZE

    try:
        with open(ruta_archivo, "rb") as f:
            while True:
                bloque = f.read(bloque_size)
                if not bloque:
                    break
                sha256.update(bloque)
        return sha256.digest()[:16]
    except OSError:
        return None


def calcular_hash_sha256_con_progreso(ruta_archivo, progress_callback=None):
    """
    Calcula un fallback de 128 bits derivado de SHA-256 informando progreso por bloques.
    """
    sha256 = hashlib.sha256()
    bloque_size = FILE_COMPARE_CHUNK_SIZE

    try:
        total_size = Path(ruta_archivo).stat().st_size
    except OSError:
        total_size = 0

    try:
        with open(ruta_archivo, "rb") as f:
            bytes_read = 0
            while True:
                bloque = f.read(bloque_size)
                if not bloque:
                    break
                sha256.update(bloque)
                bytes_read += len(bloque)
                if progress_callback is not None:
                    progress_callback(bytes_read, total_size)
        return sha256.digest()[:16]
    except OSError:
        return None


def _to_sqlite_int64(value):
    """Normaliza a entero con signo de 64 bits compatible con SQLite."""
    normalized = value & INT64_MASK
    if normalized >= INT64_SIGN_BIT:
        normalized -= (1 << 64)
    return normalized


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
        return _to_sqlite_int64(xxhash.xxh3_64_intdigest(head))

    fallback = hashlib.blake2b(head, digest_size=8).digest()
    return _to_sqlite_int64(int.from_bytes(fallback, byteorder="big", signed=False))


def calcular_hash_completo(ruta_archivo):
    """
    Hash completo de 128 bits: XXH3-128 si está disponible, fallback derivado de SHA-256.
    """
    return calcular_hash_completo_con_progreso(ruta_archivo)


def calcular_hash_completo_con_progreso(ruta_archivo, progress_callback=None):
    """
    Hash completo de 128 bits con notificación de progreso por bytes.
    """
    if xxhash is not None and hasattr(xxhash, "xxh3_128"):
        h = xxhash.xxh3_128()
        bloque_size = FILE_COMPARE_CHUNK_SIZE
        try:
            total_size = Path(ruta_archivo).stat().st_size
        except OSError:
            total_size = 0
        try:
            with open(ruta_archivo, "rb") as f:
                bytes_read = 0
                while True:
                    bloque = f.read(bloque_size)
                    if not bloque:
                        break
                    h.update(bloque)
                    bytes_read += len(bloque)
                    if progress_callback is not None:
                        progress_callback(bytes_read, total_size)
        except OSError:
            return None
        return h.digest()

    return calcular_hash_sha256_con_progreso(ruta_archivo, progress_callback)

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
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r', flush=True)
    # Print New Line on Complete
    if iteration == total: 
        print(flush=True)


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


def _iter_eligible_files(ruta_base, script_path, db_path, path_mover_abs, include_exts, exclude_exts):  # NOSONAR
    db_resolved = Path(db_path).resolve()
    stack = [Path(ruta_base).resolve()]

    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as iterator:
                entries = list(iterator)
        except OSError:
            continue

        for entry in reversed(entries):
            try:
                entry_path = Path(entry.path)
                resolved_path = entry_path.resolve(strict=False)
            except OSError:
                continue

            if _is_protected_path(resolved_path, script_path, db_resolved, path_mover_abs):
                continue

            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(resolved_path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                stat = entry.stat(follow_symlinks=False)
            except OSError:
                continue

            if not _passes_file_property_filters(entry_path, stat, include_exts, exclude_exts):
                continue

            yield resolved_path, stat


def _phase_index_files(conn, cursor, ruta_base, script_path, db_path, path_mover_abs, include_exts, exclude_exts):  # NOSONAR
    print(">> FASE 1: Indexando archivos (Actualizando DB)...")
    scan_time = time.time()
    count_scanned = 0
    batch_size = 5000
    reused_count = 0
    new_count = 0
    updated_count = 0

    existing_rows = {}

    sql_insert = "INSERT INTO files (path, size, mtime, hash, hash_error, last_seen) VALUES (?, ?, ?, ?, ?, ?)"
    sql_update = "UPDATE files SET size=?, mtime=?, hash=?, hash_error=?, last_seen=? WHERE path=?"
    sql_touch = "UPDATE files SET last_seen=?, hash_error=0 WHERE path=?"

    pending_insert = []
    pending_update = []
    pending_touch = []
    pending_batch = []

    def load_existing_rows(paths):
        if not paths:
            return
        for path_str in paths:
            cursor.execute(
                "SELECT path, size, mtime, hash FROM files WHERE path = ?",
                (path_str,),
            )
            row = cursor.fetchone()
            if row is not None:
                existing_rows[row[0]] = (row[1], row[2], row[3])

    def process_batch(batch_items):
        nonlocal reused_count, new_count, updated_count
        if not batch_items:
            return
        load_existing_rows([item[0] for item in batch_items])
        for path_str, size, mtime in batch_items:
            existing = existing_rows.get(path_str)
            if existing is None:
                pending_insert.append((path_str, size, mtime, None, 0, scan_time))
                new_count += 1
            else:
                db_size, db_mtime, _ = existing
                if size != db_size or abs(mtime - db_mtime) > 0.001:
                    pending_update.append((size, mtime, None, 0, scan_time, path_str))
                    updated_count += 1
                else:
                    pending_touch.append((scan_time, path_str))
                    reused_count += 1

    def flush_batches():
        if not (pending_insert or pending_update or pending_touch):
            return

        cursor.execute("BEGIN TRANSACTION")
        if pending_insert:
            cursor.executemany(sql_insert, pending_insert)
        if pending_update:
            cursor.executemany(sql_update, pending_update)
        if pending_touch:
            cursor.executemany(sql_touch, pending_touch)
        conn.commit()

        pending_insert.clear()
        pending_update.clear()
        pending_touch.clear()

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

        pending_batch.append((path_str, size, mtime))
        if len(pending_batch) >= batch_size:
            process_batch(pending_batch)
            pending_batch.clear()
            flush_batches()

        count_scanned += 1
        if count_scanned % batch_size == 0:
            print(f"   ... procesados {count_scanned} archivos", end='\r')

    process_batch(pending_batch)
    flush_batches()
    print(f"   -> Total escaneados: {count_scanned} | Reutilizados: {reused_count} | Nuevos: {new_count} | Actualizados: {updated_count}")
    return scan_time


def _phase_prune_db(conn, cursor, scan_time):
    print(">> FASE 2: Limpiando entradas obsoletas...")
    cursor.execute("DELETE FROM files WHERE last_seen < ?", (scan_time,))
    deleted_count = cursor.rowcount
    conn.commit()
    print(f"   -> Eliminados {deleted_count} registros de archivos que ya no existen.")


def _mark_hash_failure(cursor, path_str):
    cursor.execute("UPDATE files SET hash=NULL, hash_error=1 WHERE path=?", (path_str,))


def _print_hash_progress(processed_candidates, total_candidates, path_str, bytes_read=None, total_size=None):
    fname = os.path.basename(path_str)
    if bytes_read is not None and total_size:
        file_fraction = min(max(bytes_read / float(total_size), 0.0), 1.0)
        progress_value = (processed_candidates - 1) + file_fraction
        file_percent = file_fraction * 100.0
        suffix = f"{fname} [{file_percent:.1f}%] ({bytes_read // 1024}KB/{total_size // 1024}KB)"
        print_progress(progress_value, total_candidates, prefix=HASH_PROGRESS_PREFIX, suffix=suffix, length=30)
        return
    print_progress(processed_candidates, total_candidates, prefix=HASH_PROGRESS_PREFIX, suffix=f'{fname}', length=30)


def _print_dedup_progress(processed_items, total_items, path_str=None):
    if total_items <= 0:
        return
    suffix = Path(path_str).name if path_str else 'Completado'
    print_progress(processed_items, total_items, prefix=DEDUP_PROGRESS_PREFIX, suffix=suffix, length=30)


def _count_pending_hash_candidates(cursor):
    cursor.execute(
        "SELECT count(*) FROM files WHERE hash IS NULL AND hash_error = 0 "
        "AND size IN (SELECT size FROM files GROUP BY size HAVING count(*) > 1)"
    )
    row_count = cursor.fetchone()
    return row_count[0] if row_count else 0


def _collect_duplicate_sizes(cursor):
    cursor.execute("SELECT size FROM files GROUP BY size HAVING count(*) > 1")
    return [row[0] for row in cursor.fetchall()]


def _bucket_by_quick_signature(cursor, file_size):
    cursor.execute("SELECT path, hash, hash_error FROM files WHERE size = ?", (file_size,))
    size_group = cursor.fetchall()
    quick_groups = {}
    for path_str, _, _ in size_group:
        quick_sig = calcular_firma_rapida(path_str)
        if quick_sig is None:
            _mark_hash_failure(cursor, path_str)
            continue
        quick_groups.setdefault(quick_sig, []).append(path_str)
    return quick_groups


def _pending_paths_for_group(cursor, group_files):
    pending_paths = []
    for path_str in group_files:
        cursor.execute("SELECT hash, hash_error FROM files WHERE path=?", (path_str,))
        row = cursor.fetchone()
        if row and row[0] is None and row[1] == 0:
            pending_paths.append(path_str)
    return pending_paths


def _calculate_hash_group(cursor, pending_paths, total_candidates, processed_candidates):
    for path_str in pending_paths:
        processed_candidates += 1
        file_size = Path(path_str).stat().st_size
        last_percent = -1

        def progress_callback(bytes_read, total_size, current_path=path_str, done_count=processed_candidates):
            nonlocal last_percent
            if total_size <= 0:
                _print_hash_progress(done_count, total_candidates, current_path, bytes_read, total_size)
                return
            current_percent = int((bytes_read * 100) // total_size)
            if current_percent != last_percent or bytes_read >= total_size:
                last_percent = current_percent
                _print_hash_progress(done_count, total_candidates, current_path, bytes_read, total_size)

        _print_hash_progress(processed_candidates, total_candidates, path_str, 0, file_size)
        full_hash = calcular_hash_completo_con_progreso(path_str, progress_callback)
        if full_hash is None:
            _mark_hash_failure(cursor, path_str)
        else:
            cursor.execute("UPDATE files SET hash=?, hash_error=0 WHERE path=?", (full_hash, path_str))
    return processed_candidates


def _phase_calculate_hashes(conn, cursor):
    print(">> FASE 3: Filtro por cabecera y hash en colisiones reales...")
    total_candidates = _count_pending_hash_candidates(cursor)
    processed_candidates = 0
    hashes_calculated = 0

    if total_candidates <= 0:
        print(f"   -> Hashes completos calculados: {hashes_calculated}")
        return

    print(f"   -> Candidatos por tamaño: {total_candidates}")
    for file_size in _collect_duplicate_sizes(cursor):
        quick_groups = _bucket_by_quick_signature(cursor, file_size)
        for group_files in quick_groups.values():
            pending_paths = _pending_paths_for_group(cursor, group_files)
            if not pending_paths:
                continue
            if len(group_files) == 1:
                for path_str in pending_paths:
                    processed_candidates += 1
                    _print_hash_progress(processed_candidates, total_candidates, path_str)
                continue
            processed_candidates = _calculate_hash_group(cursor, pending_paths, total_candidates, processed_candidates)
            hashes_calculated += sum(1 for path_str in pending_paths if cursor.execute("SELECT hash FROM files WHERE path=?", (path_str,)).fetchone()[0] is not None)
        conn.commit()

    print_progress(total_candidates, total_candidates, prefix=HASH_PROGRESS_PREFIX, suffix='Completado', length=30)
    print()
    print(f"   -> Hashes completos calculados: {hashes_calculated}")


def _hash_tag_for_filename(file_hash):
    if isinstance(file_hash, (bytes, bytearray, memoryview)):
        return bytes(file_hash).hex()[:8]
    if isinstance(file_hash, int):
        # Muestra estable en hex aunque internamente esté en entero firmado.
        unsigned = file_hash & INT64_MASK
        return f"{unsigned:016x}"[:8]
    return str(file_hash)[:8]


def _files_are_identical(path_a, path_b):
    try:
        with open(path_a, "rb") as file_a, open(path_b, "rb") as file_b:
            while True:
                chunk_a = file_a.read(FILE_COMPARE_CHUNK_SIZE)
                chunk_b = file_b.read(FILE_COMPARE_CHUNK_SIZE)
                if chunk_a != chunk_b:
                    return False
                if not chunk_a:
                    return True
    except OSError:
        return None


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


def _candidate_group_matches_content(keeper_path, candidate_path):
    files_match = _files_are_identical(keeper_path, candidate_path)
    if files_match is None:
        print("  Acción:    ERROR COMPARANDO CONTENIDO ❌")
        return False
    if not files_match:
        print("  Acción:    COLISIÓN DE HASH DETECTADA, SE CONSERVAN AMBOS ⚠️")
        return False
    return True


def _process_duplicate_group(conn, cursor, mover_a, borrar_realmente, script_path, file_hash, candidates, progress_state):
    _sort_duplicate_candidates(candidates, script_path)
    keeper = candidates[0]
    to_delete = candidates[1:]

    print(f"[GRUPO DUPLICADO (x{len(candidates)})]")
    print(f"  Conservar: {keeper['path'].name}")

    processed_count = 0
    freed_bytes = 0

    for item in to_delete:
        archivo_delete = item['path']
        progress_state['processed'] += 1
        _print_dedup_progress(progress_state['processed'], progress_state['total'], archivo_delete)
        print(f"  Procesar:  {archivo_delete.name}")
        if not _candidate_group_matches_content(keeper['path'], archivo_delete):
            continue

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
            processed_count += 1
            freed_bytes += item['size']

    print("-" * 40)
    conn.commit()
    return processed_count, freed_bytes


def _phase_deduplicate(conn, cursor, mover_a, borrar_realmente, script_path):
    print(">> FASE 4: Analizando duplicados...")
    cursor.execute(
        "SELECT hash, size, count(*) as cnt FROM files "
        "WHERE hash IS NOT NULL "
        "AND hash_error = 0 "
        "GROUP BY hash, size HAVING cnt > 1"
    )
    duplicate_blocks = cursor.fetchall()

    duplicate_groups = []
    total_items = 0

    for (file_hash, file_size, _) in duplicate_blocks:
        cursor.execute("SELECT path, mtime, size FROM files WHERE hash = ? AND size = ?", (file_hash, file_size))
        candidates = [
            {'path': Path(p_str), 'mtime': m_time, 'size': f_size}
            for (p_str, m_time, f_size) in cursor.fetchall()
        ]
        if len(candidates) > 1:
            duplicate_groups.append((file_hash, file_size, candidates))
            total_items += len(candidates) - 1

    contador_duplicados = 0
    espacio_liberado = 0
    progress_state = {'processed': 0, 'total': total_items}

    if total_items > 0:
        _print_dedup_progress(0, total_items)

    for (file_hash, file_size, candidates) in duplicate_groups:
        processed_count, freed_bytes = _process_duplicate_group(
            conn, cursor, mover_a, borrar_realmente, script_path, file_hash, candidates, progress_state
        )
        contador_duplicados += processed_count
        espacio_liberado += freed_bytes

    if total_items > 0:
        _print_dedup_progress(total_items, total_items)

    return contador_duplicados, espacio_liberado

def escanear_y_eliminar(directorio, borrar_realmente, mover_a=None, includes=None, excludes=None, db_file=None):  # NOSONAR
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
    filters_key = _build_filters_key(include_exts, exclude_exts)

    conn = init_db(db_path)
    cursor = conn.cursor()
    
    contador_duplicados = 0
    espacio_liberado = 0
    success = False
    
    try:
        script_path = Path(__file__).resolve()

        scan_state = _load_scan_state(cursor, ruta_base, filters_key)
        if scan_state and scan_state['completed'] == 1:
            print(">> FASE 1: Reutilizando índice previo completado anteriormente...")
        elif scan_state and scan_state['completed'] == 0:
            print(">> FASE 1: Reanudando índice parcial existente...")
        else:
            print(">> FASE 1: Indexación inicial del directorio...")

        _save_scan_state(conn, cursor, ruta_base, filters_key, False)
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
        success = True

    except KeyboardInterrupt:
        print("\n\n!!! Interrumpido por usuario. Cerrando DB segura...")
    finally:
        if success:
            _save_scan_state(conn, cursor, ruta_base, filters_key, True)
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
    sys.stdout.reconfigure(encoding='utf-8', errors='surrogateescape')
    
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