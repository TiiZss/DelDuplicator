# LEARNINGS

## 2026-09-07

- En este workspace no existe el comando CLI `graft` disponible en PATH; se usa la carpeta graft/ como respaldo documental.
- El repo ya contiene reglas importantes en AI_INSTRUCTIONS.md y AGENTS.md, por lo que conviene consolidar y no duplicar de forma conflictiva.
- Definir politicas operativas en raiz reduce ambiguedad entre distintos agentes (Copilot, Claude, Gemini).
- Las pruebas de humo detectaron errores reales no cubiertos: faltaban imports `argparse` y `re` en delduplicator.py.
- Ejecutar Bandit con `uvx` permite auditar sin instalar dependencias globales y priorizar remediacion por severidad.
