# CHANGELOG

## [v3.0.0] - 2026-01-18 (SQLite Edition)
### Added
- **Integración SQLite DB**:
  - Índices locales persistentes en `delduplicator.db`.
  - Escaneo incremental: solo procesa archivos nuevos/modificados.
- **Fases de Ejecución**: Separación clara en Indexing, Pruning, Hashing, Dedupe.
- **Optimización Anti-Lock**: Lectura por lotes para evitar bloqueos de base de datos (`database is locked`).
- **Feedback Visual**: Barra de progreso detallada durante el cálculo de hashes.

## [v2.0.0] - 2026-01-18
### Added
- **Modo Mover (`--mover`)**: Mueve duplicados a cuarentena en lugar de borrarlos.
- **Log de Restauración**: Crea `restore_log.txt` con histórico de movimientos.
- **Smart Protection**: 
  - Detecta y protege el script `delduplicator.py` de borrarse a sí mismo.
  - Prioriza mantener el script original sobre copias.
- **Filtros**: Argumentos `--include` y `--exclude` para extensiones.

## [v1.0.0] - 2026-01-18
### Initial Release
- Escaneo recursivo básico.
- Cálculo de hash MD5+SHA1.
- Detección de duplicados.
- Modo Simulación (Dry Run) por defecto.
