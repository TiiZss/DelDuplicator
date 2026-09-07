# TROUBLESHOOTING

## 1) El comando graft no funciona

Sintoma:

- `graft` no es reconocido en terminal.

Accion:

- Usar la carpeta graft/ como mapa local.
- Verificar si el servidor MCP de graft esta configurado en .mcp.json.

Sintoma:

- Caracteres corruptos o errores por cp1252.

Accion:

- Forzar UTF-8 en lectura/escritura de archivos.
- Reconfigurar stdout/stderr en scripts Python cuando aplique.
- Ejecutar scripts con uv cuando existan dependencias externas.

## 3) Bloqueos de SQLite (database locked)

Sintoma:

- Error de base de datos bloqueada durante operaciones intensivas.

Accion:

- Separar cursores de lectura y escritura.
- Evitar UPDATE directo sobre cursor que itera SELECT.
- Cargar resultados en memoria antes de modificar filas.

## 4) Recuperacion tras mover duplicados

Sintoma:

- Se movieron archivos por error.

Accion:

- Usar restore.py con el log de restauracion disponible.
- Verificar rutas origen/destino antes de restaurar.
