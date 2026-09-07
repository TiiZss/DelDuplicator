# Decision Log

## 2026-09-07 - Crear mapa operativo en raiz

- Decision: agregar CLAUDE.md en la raiz como mapa operativo equivalente para este entorno.
- Motivo: unificar reglas de trabajo y hacerlas auditable dentro del repo.
- Impacto: mejora consistencia entre agentes y tareas.

## 2026-09-07 - Registrar metadatos de flujo

- Decision: crear MEMORY.md, LEARNINGS.md y decisions.md.
- Motivo: cumplir requisito de trazabilidad de contexto, lecciones y decisiones.
- Impacto: facilita auditorias tecnicas y continuidad del trabajo.

## 2026-09-07 - Gestion de restricciones MCP

- Decision: registrar como politica objetivo el uso minimo de MCP (GitHub, Context7, Playwright MCP, Filesystem, Sentry).
- Motivo: la disponibilidad de MCP depende del entorno instalado, no solo del repo.
- Impacto: cuando falte algun MCP, se documenta bloqueo y alternativa en lugar de inventar cumplimiento.

## 2026-09-07 - Checklist pre-release en Kanban

- Decision: incorporar una lista de verificacion pre-release (Definition of Done) en KANBAN.md.
- Motivo: estandarizar calidad minima antes de publicar cambios.
- Impacto: reduce regresiones y asegura alineacion de pruebas, seguridad y documentacion.

## 2026-09-07 - Plantilla reutilizable por rama feature

- Decision: agregar una plantilla de feature en KANBAN.md para copiar por funcionalidad.
- Motivo: uniformar trazabilidad por rama y facilitar auditoria tecnica.
- Impacto: mejora consistencia de entrega y evidencia de calidad por feature.

## 2026-09-07 - Primera instancia de feature creada

- Decision: crear la primera instancia `workflow-governance-baseline` en KANBAN.md.
- Motivo: activar uso real de la plantilla por rama y no dejarla solo como formato.
- Impacto: el equipo ya tiene un registro operativo con checklist y evidencias pendientes.

## 2026-09-07 - Correccion de bloqueadores runtime y hardening

- Decision: corregir `NameError` en CLI agregando imports faltantes (`argparse`, `re`) en delduplicator.py.
- Motivo: las pruebas de humo detectaron que el flujo CLI no iniciaba o fallaba en fase de deduplicacion.
- Impacto: el comando `--help` y el flujo real de mover duplicados vuelven a funcionar.

- Decision: corregir hallazgos de seguridad accionables en delduplicator.py (f-string SQL innecesaria y `except` sin clase).
- Motivo: reducir riesgo y eliminar hallazgos medium de Bandit.
- Impacto: auditoria actual queda con 0 hallazgos medium/high y 2 low en GUI por uso de `subprocess`.

## 2026-09-07 - Cierre de hallazgos low en GUI

- Decision: mantener `subprocess` en GUI con anotaciones `# nosec` en puntos auditados (B404, B603).
- Motivo: la ejecucion de scripts locales desde GUI es un requisito funcional actual y se realiza sin `shell=True`.
- Impacto: Bandit queda sin hallazgos abiertos en el estado actual.

## 2026-09-07 - Activacion real de filtros include/exclude

- Decision: implementar aplicacion efectiva de `--include` y `--exclude` en el escaneo de archivos.
- Motivo: los parametros existian en CLI pero no estaban afectando la seleccion de ficheros.
- Impacto: mejora funcionalidad y elimina warnings por parametros no usados.

## 2026-09-07 - Deuda tecnica pendiente

- Decision: posponer refactor de complejidad cognitiva de `escanear_y_eliminar`.
- Motivo: requiere separacion estructural amplia para cumplir umbral del analizador (15).
- Impacto: queda un warning de calidad no bloqueante para planificar en una feature dedicada.

## 2026-09-07 - Refactor de complejidad completado

- Decision: descomponer `escanear_y_eliminar` en helpers por fase y predicados de filtrado.
- Motivo: cerrar el warning de complejidad cognitiva y mantener legibilidad/seguridad.
- Impacto: Problems en verde para archivos tocados y comportamiento funcional validado.
