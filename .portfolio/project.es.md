---
description: >-
  Contexto externo por proyecto y procesos de ingeniería específicos para agentes.
metaDescription: >-
  Harness conserva conocimiento útil y contexto de continuación en archivos Markdown locales, fuera del repositorio. Quince skills independientes apoyan la planificación, implementación, revisión y operaciones Git.
summary: >-
  Harness proporciona a cada proyecto un entorno externo compartido por sus worktrees de Git. Quince skills independientes cubren contexto, planificación modular, handoffs, coordinación de agentes y procesos de ingeniería. Los agentes consultan solo el material necesario para la tarea.
highlights:
  - un entorno por proyecto y sus worktrees
  - quince skills independientes
  - contexto en archivos consultado cuando hace falta
  - actualizaciones atómicas de Markdown sin reservas de archivos
---

Harness proporciona a cada proyecto un entorno externo compartido por sus worktrees de Git. Quince skills independientes cubren contexto, planificación modular, handoffs, coordinación de agentes y procesos de ingeniería. Los agentes consultan solo el material necesario para la tarea.

## Contexto del proyecto fuera del repositorio

Cada repositorio o monorepo tiene un entorno. El conocimiento útil se guarda en archivos Markdown organizados por tema. Los planes temporales, la configuración del equipo y el contexto de continuación existen solo cuando son necesarios; los pequeños cambios individuales no requieren un registro de trabajo.

## Procesos específicos y contexto delimitado

Los planes macro son modulares independientemente del número de agentes. Los frentes de implementación y revisión pueden referenciar los mismos entregables y mantener separados sus contextos de ejecución. Los handoffs transfieren responsabilidad mediante referencias a archivos canónicos, sin copiar conversaciones.

## Worktrees y persistencia segura

Las nuevas worktrees se ubican dentro del entorno del proyecto. Los agentes que colaboran en un frente pueden alternar la escritura; los frentes independientes usan checkouts separados. El helper de Python protege las actualizaciones de Markdown frente a cambios realizados desde la última lectura.

Al completar un trabajo, se consolida el conocimiento útil y se elimina el contexto temporal. El material necesario para otro frente o un handoff pendiente permanece disponible. Retirar una worktree es una decisión separada.
