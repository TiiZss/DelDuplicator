# Architecture

## Resumen

DelDuplicator es una herramienta para detectar y gestionar archivos duplicados con dos superficies:

- CLI: flujo principal de escaneo y accion sobre duplicados.
- GUI: interfaz para ejecucion y restauracion asistida.

## Componentes

- delduplicator.py: motor principal de indexado, hashing y decisiones de duplicado.
- delduplicator_gui.py: interfaz grafica para operar el motor.
- restore.py: restauracion basada en logs de movimiento.
- delduplicator.db: persistencia SQLite para acelerar ejecuciones repetidas.
- dest/: carpeta de salida de ejemplo para archivos movidos y logs.
- graft/: mapa estructural del repositorio.

## Principios tecnicos

- Seguridad primero: dry-run por defecto en acciones destructivas.
- Trazabilidad: logs para operaciones de movimiento/restauracion.
- Rendimiento: indexado con SQLite y hashing bajo demanda.

## Mapa operativo

- Este repo usa CLAUDE.md en raiz como mapa de trabajo para agentes.
- AGENTS.md y graft/ complementan la navegacion por codigo y contexto.
