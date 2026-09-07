# CHANGELOG

## [Unreleased]

### Fixed - Unreleased

- CLI: corregido `NameError` por imports faltantes (`argparse`, `re`) en `delduplicator.py`.
- CLI: aplicado filtrado real de extensiones para `--include` y `--exclude`.
- Mantenibilidad: refactor de `escanear_y_eliminar` en helpers por fases para reducir complejidad cognitiva.
- Seguridad: eliminado hallazgo medium de Bandit al reemplazar SQL `f-string` por string literal.
- Robustez: reemplazado `except` generico por `except OSError` en escritura de `restore_log`.
- Seguridad GUI: revisado uso de `subprocess` y cerrados hallazgos low de Bandit con anotaciones auditadas.

### Added - Unreleased

- Documentacion operativa en raiz:
  - `CLAUDE.md`
  - `MEMORY.md`
  - `LEARNINGS.md`
  - `decisions.md`
  - `KANBAN.md`
  - `ARCHITECTURE.md`
  - `TROUBLESHOOTING.md`

## [v3.0.0] - 2026-01-18 (SQLite Edition)

### Added - v3.0.0

- **Integracion SQLite DB**:
  - Indices locales persistentes en `delduplicator.db`.
  - Escaneo incremental: solo procesa archivos nuevos/modificados.
- **Fases de Ejecucion**: Separacion clara en Indexing, Pruning, Hashing, Dedupe.
- **Optimizacion Anti-Lock**: Lectura por lotes para evitar bloqueos de base de datos (`database is locked`).
- **Feedback Visual**: Barra de progreso detallada durante el calculo de hashes.

## [v2.0.0] - 2026-01-18

### Added - v2.0.0

- **Modo Mover (`--mover`)**: Mueve duplicados a cuarentena en lugar de borrarlos.
- **Log de Restauracion**: Crea `restore_log.txt` con historico de movimientos.
- **Smart Protection**:
  - Detecta y protege el script `delduplicator.py` de borrarse a si mismo.
  - Prioriza mantener el script original sobre copias.
- **Filtros**: Argumentos `--include` y `--exclude` para extensiones.

## [v1.0.0] - 2026-01-18

### Initial Release - v1.0.0

- Escaneo recursivo basico.
- Calculo de hash MD5+SHA1.
- Deteccion de duplicados.
- Modo Simulacion (Dry Run) por defecto.
