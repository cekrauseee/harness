---
description: >-
  Contexto externo por proyecto y procesos de ingeniería específicos para agentes.
metaDescription: >-
  Harness conserva conocimiento útil y contexto de continuación en archivos Markdown locales, fuera del repositorio. Diez skills independientes apoyan la planificación, deliberación entre pares, implementación, revisión y operaciones Git en Codex y Claude Code.
summary: >-
  Harness proporciona a cada proyecto un entorno externo compartido por sus worktrees de Git. Diez skills independientes cubren contexto, planificación modular, handoffs, coordinación de agentes, deliberación entre pares y procesos de ingeniería en Codex y Claude Code, con un único archivo de instrucciones compartido. Los procesos orientan a los agentes hacia el contexto relevante para cada tarea.
highlights:
  - un entorno por proyecto y sus worktrees
  - diez skills independientes para Codex y Claude Code
  - contexto en archivos consultado cuando hace falta
  - actualizaciones atómicas de Markdown sin reservas de archivos
---

Harness proporciona a cada proyecto un entorno externo compartido por sus worktrees de Git. Diez skills independientes cubren contexto, planificación modular, handoffs, coordinación de agentes, deliberación entre pares y procesos de ingeniería en Codex y Claude Code, con un único archivo de instrucciones compartido. Los procesos orientan a los agentes hacia el contexto relevante para cada tarea.

## Contexto del proyecto fuera del repositorio

Cada repositorio o monorepo tiene un entorno local. Su mapa resumido ayuda a los agentes a descubrir restricciones aplicables y encontrar contexto relevante. El conocimiento útil se guarda en archivos Markdown organizados por tema. Los planes temporales, la configuración del equipo y el contexto de continuación existen solo cuando son necesarios; los pequeños cambios individuales no requieren un registro de trabajo.

## Procesos específicos y contexto delimitado

Los planes macro son modulares independientemente del número de agentes. Los frentes de implementación y revisión pueden referenciar los mismos entregables y mantener separados sus contextos de ejecución. Los handoffs transfieren responsabilidad mediante referencias a archivos canónicos, sin copiar conversaciones.

Cuando se solicita, la deliberación entre pares reúne a los agentes para desarrollar un análisis, una decisión o una propuesta. Los participantes aportan y cuestionan ideas en igualdad, refinan una síntesis conjunta y conservan los desacuerdos relevantes. La coordinación organiza el intercambio sin determinar qué perspectiva debe prevalecer.

## Dos hosts, un solo conjunto de instrucciones

Un único archivo de instrucciones sirve a Codex y Claude Code: Codex lo lee directamente, Claude Code lo importa y cada host aplica una breve sección propia. La mecánica de cada host, como la memoria y las worktrees gestionadas, queda a cargo del plugin; la persona define solo decisiones prácticas, como idioma, convenciones de ramas y política de pruebas.

## Worktrees y persistencia segura

Las worktrees creadas por Harness se ubican dentro del entorno del proyecto; las gestionadas por el host se aceptan donde están. Los agentes que colaboran en un frente pueden alternar la escritura; los frentes independientes usan checkouts separados. El helper de Python protege las actualizaciones de Markdown frente a cambios realizados desde la última lectura.

Al completar un trabajo, se consolida el conocimiento útil y se preservan los entregables que deban conservarse, con referencias actualizadas, antes de mover el contexto temporal a la papelera del entorno, que la persona vacía cuando quiere. El material necesario para otro frente o un handoff pendiente permanece disponible. Retirar una worktree es una decisión separada.
