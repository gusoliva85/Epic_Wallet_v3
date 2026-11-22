# Documentación

## Un solo documento vivo

Desde la revisión del 07/10/2026 **no hay un documento por fase**. El plan original pedía 18, uno al cerrar cada fase; eran unas 9.000 líneas de prosa para escribir y después mantener sincronizada con el código, y la aplicación la usan pocas personas conocidas.

Lo reemplaza **un solo** [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md), que se actualiza cuando algo cambia de verdad.

| Documento | Estado |
|---|---|
| [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md) | Al día |

## Lo que ya estaba escrito

| Fase | Documento | Estado |
|---|---|---|
| 1 · Sistema de estilo y esqueleto visual | [FASE_01_SISTEMA_DE_ESTILO.md](FASE_01_SISTEMA_DE_ESTILO.md) | Cerrada el 04/10/2026 |

> No se amplía ni se mantiene al día; vale como registro de lo que se montó y por qué. Donde hable de **dos esquemas de base de datos** (`public` y `dev`), quedó desactualizado: el proyecto usa **un solo esquema**. Ver `02_Documento_Tecnico.md` §4.1.1.

> El documento de la Fase 0 se borró en F14-T04: era el instructivo para montar una infraestructura de terceros que el proyecto dejó de usar, y mantenerlo sólo podía desorientar. Está en el historial de Git. Lo que lo reemplaza son las fases 15 y 16 del roadmap.

Las capturas de [`capturas/`](capturas/) son de la Fase 1 y no se mantienen al día.

---

**Las fuentes del proyecto**

| Documento | Qué contiene |
|---|---|
| [`CLAUDE.md`](../CLAUDE.md) | Resumen de arranque: stack, reglas, lo que no se puede romper |
| [`01_Documento_General.md`](../documentacion/01_Documento_General.md) | **Qué** hace la aplicación |
| [`02_Documento_Tecnico.md`](../documentacion/02_Documento_Tecnico.md) | **Cómo** se construye |
| [`03_Roadmap.md`](../documentacion/03_Roadmap.md) | **En qué orden**, tarea por tarea |
| [`04_Migracion_a_Contabo.md`](../documentacion/04_Migracion_a_Contabo.md) | El traslado al servidor propio |
