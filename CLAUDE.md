# Mapa Operativo del Proyecto (equivalente a CLAUDE.md)

Este archivo define como debe trabajar cualquier agente en este repositorio.
Las carpetas almacenan informacion; este mapa define como interpretarlas y usarlas.

## 1) Reglas base

- No inventar datos, rutas, resultados ni salidas de comandos.
- Cuestionar supuestos del usuario cuando falte evidencia tecnica.
- Planificar antes de codificar.
- Mantener estructura profesional y ordenada.
- Codificacion estandar: UTF-8.

## 2) Flujo obligatorio por tarea

1. Revisar contexto del repo con Graft (si CLI no esta disponible, usar la carpeta graft/ como mapa).
2. Definir plan corto y criterio de exito.
3. Implementar en rama dedicada por funcionalidad.
4. Ejecutar pruebas y auditoria de seguridad segun aplique.
5. Corregir errores del panel Problems antes de publicar.
6. Alinear documentacion (README, CHANGELOG, docs/kanban.md, docs/architecture.md, docs/troubleshooting.md, graft si aplica).
7. Preparar tag y release cuando se publique en GitHub.

## 3) Python

- Usar entorno virtual.
- Usar uv en lugar de pip siempre que sea viable.
- Evitar dependencias globales del sistema.

## 4) Reutilizacion antes de construir

- Antes de crear una funcionalidad nueva, revisar proyectos similares en GitHub para reutilizar base.
- Regla: no reinventar la rueda; mejorarla.

## 5) MCP y herramientas

Politica objetivo minima por proyecto:

- GitHub
- Context7
- Playwright MCP
- Filesystem
- Sentry

Nota operativa:

- La disponibilidad real depende del entorno del agente y de extensiones instaladas.
- Si falta algun MCP, documentar el bloqueo en decisions.md y proponer alternativa.

## 6) Skills externas solicitadas por el usuario

Rutas solicitadas para revisar por proyecto:

- D:/Scripts/Z-externos/ECC
- D:/Scripts/Z-externos/Anthropic-Cybersecurity-Skills

Regla:

- Revisar skills aplicables a la tarea activa e incorporar solo las relevantes.
- No incluir skills innecesarias.

## 7) Metadatos de trabajo en raiz

- MEMORY.md: contexto duradero del proyecto.
- LEARNINGS.md: lecciones aprendidas verificadas.
- decisions.md: auditoria de decisiones y trade-offs.

## 8) Humanizacion de texto

- Si hay texto generado para entregables del proyecto, pasar por Humanizer cuando este disponible: [Humanizer](https://github.com/blader/humanizer).
- Si la herramienta no esta instalada, registrar la limitacion y dejar pendiente explicito.

## 9) Diagrams y diseno

- Usar Diagram Design como referencia cuando se requiera arquitectura visual: [Diagram Design](https://github.com/cathrynlavery/diagram-design).

## 10) Estado inicial en este repo

- Existe AGENTS.md con reglas de Graft.
- Existe AI_INSTRUCTIONS.md con normas Python/UTF-8/seguridad.
- Este archivo consolida el marco operativo equivalente a CLAUDE.md para este entorno.
