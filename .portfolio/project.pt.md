---
description: >-
  Contexto externo por projeto e processos de engenharia específicos para agentes.
metaDescription: >-
  O Harness mantém conhecimento útil e contexto de continuação em arquivos Markdown locais, fora do repositório. Quinze skills independentes apoiam planejamento, implementação, revisão e operações Git.
summary: >-
  O Harness oferece a cada projeto um ambiente externo compartilhado por suas worktrees Git. Quinze skills independentes cobrem contexto, planejamento modular, handoffs, coordenação de agentes e processos de engenharia. Os agentes leem apenas o material necessário à tarefa.
highlights:
  - um ambiente por projeto e suas worktrees
  - quinze skills independentes
  - contexto em arquivos consultado quando necessário
  - atualizações atômicas de Markdown sem reservas de arquivos
---

O Harness oferece a cada projeto um ambiente externo compartilhado por suas worktrees Git. Quinze skills independentes cobrem contexto, planejamento modular, handoffs, coordenação de agentes e processos de engenharia. Os agentes leem apenas o material necessário à tarefa.

## Contexto do projeto fora do repositório

Cada repositório ou monorepo tem um ambiente. O conhecimento útil fica em arquivos Markdown organizados por assunto. Planos temporários, configuração de equipe e contexto de continuação existem apenas quando necessários; pequenas correções solo dispensam registro de trabalho.

## Processos específicos e contexto delimitado

Planos macro são modulares independentemente da quantidade de agentes. Frentes de implementação e revisão podem referenciar os mesmos entregáveis, mantendo separados seus contextos de execução. Handoffs transferem responsabilidade por referências aos arquivos canônicos, sem copiar conversas.

## Worktrees e persistência segura

Novas worktrees ficam dentro do ambiente do projeto. Agentes que colaboram em uma frente podem alternar a escrita; frentes independentes usam checkouts separados. O utilitário Python protege atualizações de Markdown contra a substituição de mudanças feitas depois da leitura.

Ao concluir um trabalho, o conhecimento útil é consolidado e o contexto temporário é removido. Material ainda necessário a outra frente ou a um handoff pendente permanece disponível. A retirada de uma worktree é uma decisão separada.
