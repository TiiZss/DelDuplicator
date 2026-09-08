# DelDuplicator

Script profesional para la detección y eliminación (o movimiento seguro) de archivos duplicados. Optimizado para grandes volúmenes con base de datos SQLite y protección inteligente.

![Release](https://img.shields.io/github/v/release/TiiZss/DelDuplicator?style=flat-square)
![License](https://img.shields.io/github/license/TiiZss/DelDuplicator?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)
![Status](https://img.shields.io/badge/Status-Stable-green?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=flat-square&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/TiiZss)

## 🚀 Características

*   **⚡ Ultra Rápido**: Utiliza **SQLite** para indexar archivos localmente. Las ejecuciones repetidas son prácticamente instantáneas.
*   **🛡️ Seguridad Primero**:
    *   **Anti-Auto-Bucle**: Impide escanear la carpeta de destino para evitar bucles infinitos.
    *   **Protección de Sistema**: Ignora carpetas críticas (`Windows`, `Program Files`, `.git`) por defecto.
    *   **Hardlinks**: Detecta y respeta enlaces físicos del sistema de archivos.
    *   **Dry Run**: No elimina nada por defecto.
*   **🧠 Inteligente**:
    *   Detecta cual es la "copia" (`archivo (1).txt`) y prefiere mantener el original (`archivo.txt`).
    *   Barra de progreso visual durante el hashing.
    *   Manejo de bloqueos de base de datos (`database locked`).
*   **🚑 Undo / Restaurar**:
    *   Incluye herramienta para deshacer movimientos usando el log generado.

## 🛠️ Instalación

1.  Clona el repositorio:
    ```bash
    git clone https://github.com/TiiZss/DelDuplicator.git
    ```
2.  (Opcional) Instala [`uv`](https://github.com/astral-sh/uv) para gestión de dependencias moderna.

## 💻 Uso (Inicio Rápido)

### Interfaz Gráfica (Windows)
Simplemente haz doble clic en **`start_gui.bat`**.

![GUI Screenshot](https://raw.githubusercontent.com/TiiZss/DelDuplicator/master/gui_preview.png)

### Línea de Comandos

**1. Escaneo de Prueba (Simulación)**
```powershell
python delduplicator.py "D:\Mis Documentos"
```

**2. Mover Duplicados (Recomendado)**
Mueve los archivos repetidos a una carpeta de cuarentena.
```powershell
python delduplicator.py . --mover "D:\Duplicados_Cuarentena"
```
*Si te equivocas, puedes usar la pestaña "Restaurar" en la GUI.*

**3. Borrado Permanente**
```powershell
python delduplicator.py . --borrar
```

## 📝 Changelog

Consulta el [CHANGELOG.md](CHANGELOG.md) para ver el historial de cambios.

## 🧭 Documentación Operativa

Este repositorio incluye un mapa operativo y metadatos de trabajo para agentes:

* `CLAUDE.md`: mapa operativo del proyecto (equivalente para uso en este entorno).
* `MEMORY.md`: contexto duradero del proyecto.
* `LEARNINGS.md`: lecciones aprendidas verificadas.
* `decisions.md`: registro auditable de decisiones.
* `docs/kanban.md`: estado de trabajo por columnas.
* `docs/architecture.md`: visión de componentes y principios.
* `docs/troubleshooting.md`: incidencias frecuentes y resolución.

Recomendación para ejecución Python con dependencias: priorizar `uv run` sobre llamadas directas a `python`.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - mira el archivo [LICENSE](LICENSE) para detalles.

## 🤝 Contribuir y Apoyo

¿Te ha sido útil este proyecto? ¡Considera invitarme a un café para mantener el código despierto! ☕

Tu apoyo ayuda a mantener las actualizaciones y crear nuevas herramientas open source.

<a href="https://www.buymeacoffee.com/TiiZss" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

---
Hecho con ❤️ por [TiiZss](https://github.com/TiiZss)
