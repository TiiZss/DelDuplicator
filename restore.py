# /// script
# dependencies = []
# ///

import argparse
import os
import shutil
from pathlib import Path


def _is_within(base_path, candidate_path):
    try:
        return candidate_path.resolve(strict=False).is_relative_to(base_path.resolve(strict=False))
    except AttributeError:
        base_resolved = base_path.resolve(strict=False)
        candidate_resolved = candidate_path.resolve(strict=False)
        return str(candidate_resolved).startswith(str(base_resolved) + os.sep)


def _parse_restore_line(linea):
    partes = linea.split(" | ", 2)
    if len(partes) != 3:
        return None
    return Path(partes[1]), Path(partes[2])


def _restore_entry(ruta_log, src_original, dst_actual):
    if not _is_within(ruta_log.parent, dst_actual):
        print(f"[SKIP] Destino fuera de cuarentena: {dst_actual}")
        return False

    if not dst_actual.exists():
        print(f"[MISSING] No existe en cuarentena: {dst_actual.name}")
        return False

    try:
        if not src_original.parent.exists():
            src_original.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(dst_actual), str(src_original))
        print(f"[OK] Restaurado: {src_original.name}")

        try:
            dst_actual.parent.rmdir()
        except OSError:
            pass

        return True
    except Exception as e:
        print(f"[ERROR] Falló mover {dst_actual} -> {src_original}: {e}")
        return False

def restaurar_archivos(log_path):
    ruta_log = Path(log_path).resolve()
    if not ruta_log.exists():
        print(f"Error: No se encuentra el archivo de log: {ruta_log}")
        return

    print(f"--- Iniciando Restauración desde: {ruta_log.name} ---")
    
    lineas_fail = []
    lineas_restauradas = 0
    
    with open(ruta_log, "r", encoding="utf-8") as f:
        contenido = f.readlines()

    total = len(contenido)
    print(f"Entradas encontradas: {total}")

    for idx, linea in enumerate(contenido):
        linea = linea.strip()
        if not linea: continue
        
        # Formato: FECHA | ORIGEN | DESTINO
        parsed_line = _parse_restore_line(linea)
        if parsed_line is None:
            print(f"[SKIP] Formato inválido: {linea}")
            lineas_fail.append(linea)
            continue

        src_original, dst_actual = parsed_line
        if _restore_entry(ruta_log, src_original, dst_actual):
            lineas_restauradas += 1
        else:
            lineas_fail.append(linea)

    print("\n--- Resumen ---")
    print(f"Restaurados: {lineas_restauradas}/{total}")
    
    # Reescribir log con solo lo fallido? O renombrarlo?
    # Mejor renombrar el log viejo a .bak y guardar los fallos en uno nuevo
    bkp_log = ruta_log.with_suffix(".log.bak")
    shutil.move(str(ruta_log), str(bkp_log))
    print(f"Log original renombrado a: {bkp_log.name}")
    
    if lineas_fail:
        with open(ruta_log, "w", encoding="utf-8") as f:
            for l in lineas_fail:
                f.write(l + "\n")
        print(f"Se ha creado un nuevo log con {len(lineas_fail)} entradas fallidas/pendientes.")
    else:
        print("Restauración completa. Log limpio.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de Restauración (Undo) para DelDuplicator.")
    parser.add_argument("log_file", help="Ruta al archivo restore_log.txt")
    args = parser.parse_args()
    
    restaurar_archivos(args.log_file)
