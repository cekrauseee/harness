---
description: >-
  Conocimiento persistente y coordinación del trabajo entre agentes, tareas y
  repositorios.
metaDescription: >-
  Continuity mantiene disponibles entre tareas las decisiones relevantes, los
  hallazgos útiles y el trabajo pendiente. El conocimiento se guarda en
  archivos Markdown locales, fuera de los repositorios.
summary: >-
  Continuity mantiene disponibles entre tareas las decisiones relevantes, los
  hallazgos útiles y el trabajo pendiente. Lo creé para que el contexto pudiera
  conservarse cuando el trabajo pasa a una conversación nueva o a otro agente.
  Cuatro skills independientes guían la configuración de entornos, la
  recuperación del contexto, el mantenimiento del conocimiento y la
  coordinación de cambios compartidos.
highlights:
  - conocimiento en archivos Markdown locales, fuera de los repositorios
  - cuatro skills independientes
  - recuperación del contexto cuando la tarea lo requiere
  - reservas de archivos y coordinación atómica
---

Continuity mantiene disponibles entre tareas las decisiones relevantes, los hallazgos útiles y el trabajo pendiente. Lo creé para que el contexto pudiera conservarse cuando el trabajo pasa a una conversación nueva o a otro agente.

Cuatro skills independientes guían la configuración de entornos, la recuperación del contexto, el mantenimiento del conocimiento y la coordinación de cambios compartidos.

## Compartir conocimiento entre proyectos

El conocimiento se guarda en archivos Markdown locales, fuera de los repositorios. Los proyectos relacionados pueden pertenecer al mismo entorno y compartir notas y contribuciones, manteniendo la identidad propia de cada directorio de trabajo.

La pertenencia al entorno es explícita. Una contribución puede abarcar archivos de varios repositorios sin perder el registro del proyecto en el que comenzó. Los worktrees de Git comparten el entorno de su repositorio, pero siguen siendo espacios de trabajo distintos.

## Recuperar el contexto cuando la tarea lo requiere

Las skills indican a los agentes que comiencen por la solicitud y la información ya disponible. El conocimiento guardado se consulta cuando una decisión anterior o un dato que falta podría influir en la forma de abordar la tarea.

Las notas conservan su alcance, sus fuentes y sus incertidumbres. Las decisiones confirmadas se mantienen diferenciadas de las hipótesis, y la información que ya está documentada adecuadamente en un proyecto puede permanecer en su fuente original.

## Coordinar cambios y trabajo pendiente

Un helper de Python comprueba si hay reservas de archivos que se solapan y protege las actualizaciones de conocimiento para evitar que sobrescriban contenido que cambió desde la última lectura.

Cuando una tarea debe retomarse más adelante, su registro de contribución guarda un resumen del estado actual y de los siguientes pasos. Una vez completado el trabajo, se consolida el conocimiento relevante y la contribución, junto con sus reservas, se elimina en una única operación atómica.

Las reservas coordinan a los agentes que siguen el mismo procedimiento. No impiden las modificaciones realizadas con otras herramientas, una limitación importante de este enfoque.
