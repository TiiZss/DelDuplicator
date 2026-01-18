# /// script
# dependencies = []
# ///

import os
import shutil
import argparse
from pathlib import Path

def restaurar_archivos(log_path):
    ruta_log = Path(log_path).resolve()
    if not ruta_log.exists():
        print(f"Error: No se encuentra el archivo de log: {ruta_log}")
        return

    print(f"--- Iniciando Restauración desde: {ruta_log.name} ---")
    
    lineas_ok = []
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
        partes = linea.split(" | ")
        if len(partes) < 3:
            print(f"[SKIP] Formato inválido: {linea}")
            lineas_fail.append(linea)
            continue
            
        src_original = Path(partes[1])
        dst_actual = Path(partes[2])
        
        if dst_actual.exists():
            try:
                # Crear carpeta padre original si no existe
                if not src_original.parent.exists():
                    src_original.parent.mkdir(parents=True, exist_ok=True)
                
                # Mover de vuelta
                shutil.move(str(dst_actual), str(src_original))
                print(f"[OK] Restaurado: {src_original.name}")
                lineas_restauradas += 1
                
                # Intentar borrar carpeta contenedora de destino si quedó vacía
                try:
                    dst_actual.parent.rmdir() # Solo borra si está vacía
                except OSError: pass
                
            except Exception as e:
                print(f"[ERROR] Falló mover {dst_actual} -> {src_original}: {e}")
                lineas_fail.append(linea)
        else:
            print(f"[MISSING] No existe en cuarentena: {dst_actual.name}")
            # Si no existe, no podemos restaurar, pero tampoco mantenemos la línea
            # O quizás sí para auditoría? Asumimos que ya fue gestionado manualmente.
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
