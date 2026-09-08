# KANBAN

## Backlog

- Revisar proyectos similares en GitHub para posibles bases reutilizables.
- Definir politica de ramas por funcionalidad y convencion de nombres.
- Verificar disponibilidad de MCP requeridos en el entorno local.

## Pre-release Checklist (Definition of Done)

- Tests: ejecucion en verde de las pruebas aplicables a la funcionalidad.
- Security audit: analisis de seguridad ejecutado y hallazgos criticos corregidos.
- Problems panel: sin errores relevantes pendientes en archivos tocados.
- Documentacion alineada: README, CHANGELOG, docs/kanban.md, docs/architecture.md, docs/troubleshooting.md.
- Graft: contexto revisado desde graft/ y actualizacion del grafo si hubo cambios grandes.
- GitHub release: tag y notas de release preparados cuando aplique.
- Humanizer: texto generado pasado por Humanizer cuando la herramienta este disponible.

## Feature Template (copiar por rama)

### Feature: NOMBRE_CORTO

- Branch: feature/NOMBRE_CORTO
- Objetivo: descripcion breve de la funcionalidad.
- Responsable: nombre o equipo.
- Estado: Backlog | In Progress | Review | Done
- Fecha inicio: YYYY-MM-DD
- Fecha objetivo: YYYY-MM-DD

Checklist de ejecucion:

- [ ] Revisar repos similares en GitHub y documentar reutilizacion.
- [ ] Implementacion terminada y revisada.
- [ ] Tests en verde.
- [ ] Auditoria de seguridad sin hallazgos criticos abiertos.
- [ ] Problems panel limpio en archivos tocados.
- [ ] Documentacion actualizada: README, CHANGELOG, docs/kanban.md, docs/architecture.md, docs/troubleshooting.md.
- [ ] Graft revisado y actualizado si hubo cambios grandes.
- [ ] Texto generado humanizado con Humanizer (si disponible).
- [ ] Tag y release listos para publicacion (si aplica).

Evidencias:

- PR:
- Commit(s):
- Resultado tests:
- Resultado auditoria seguridad:

## Feature Instances

### Feature: workflow-governance-baseline-clean

- Branch: feature/workflow-governance-baseline-clean
- Objetivo: establecer marco operativo del repo para ejecucion con calidad y trazabilidad, reforzando runtime, seguridad y governance.
- Responsable: Copilot + mantenimiento del repositorio.
- Estado: Done
- Fecha inicio: 2026-09-07
- Fecha objetivo: 2026-09-07

Checklist de ejecucion:

- [x] Revisar repos similares en GitHub y documentar reutilizacion.
- [x] Implementacion terminada y revisada.
- [x] Tests en verde.
- [x] Auditoria de seguridad sin hallazgos criticos abiertos.
- [x] Problems panel limpio en archivos tocados.
- [x] Documentacion actualizada: README, CHANGELOG, docs/kanban.md, docs/architecture.md, docs/troubleshooting.md.
- [x] Graft revisado y actualizado si hubo cambios grandes.
- [ ] Texto generado humanizado con Humanizer (si disponible).
- [ ] Tag y release listos para publicacion (si aplica).

Evidencias:

- PR: https://github.com/TiiZss/DelDuplicator/pull/1
- Commit(s): rama actual en feature/workflow-governance-baseline-clean
- Resultado tests: validacion CLI y flujo real de deduplicacion con movimiento a carpeta de destino en verde.
- Resultado auditoria seguridad: Bandit ejecutado con `uvx`; sin hallazgos relevantes para archivos tocados.
- Problems pendientes: ninguno en archivos tocados de esta feature.
- Release draft: `docs/releases/v3.1.0.md` preparado y alineado con el resultado verificado.
- Repos similares revisados:
  - [Duplicate-files-finder-python](https://github.com/Skillleading-Mohit/Duplicate-files-finder-python)
  - [dupeFinderC](https://github.com/jlantz4/dupeFinderC)

## In Progress

- Ninguna tarea en progreso.

## Review

- Ninguna tarea en revision.

## Done

- Creado mapa operativo en CLAUDE.md.
- Creados metadatos de flujo: MEMORY.md, LEARNINGS.md, decisions.md.
- Definido checklist pre-release dentro de docs/kanban.md.
- Feature workflow-governance-baseline implementada y commiteada en c57183d.
