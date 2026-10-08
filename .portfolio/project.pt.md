---
description: >-
  Contexto externo por projeto e processos de engenharia específicos para agentes.
metaDescription: >-
  O Harness mantém conhecimento útil e contexto de continuação em arquivos Markdown locais, fora do repositório. Dez skills independentes apoiam planejamento, deliberação entre pares, implementação, revisão e operações Git no Codex e no Claude Code.
summary: >-
  O Harness oferece a cada projeto um ambiente externo compartilhado por suas worktrees Git. Dez skills independentes cobrem contexto, planejamento modular, handoffs, coordenação de agentes, deliberação entre pares e processos de engenharia no Codex e no Claude Code, com um único arquivo de instruções compartilhado. Os processos orientam os agentes a buscar o contexto relevante para cada tarefa.
highlights:
  - um ambiente por projeto e suas worktrees
  - dez skills independentes para Codex e Claude Code
  - contexto em arquivos consultado quando necessário
  - atualizações atômicas de Markdown sem reservas de arquivos
---

O Harness oferece a cada projeto um ambiente externo compartilhado por suas worktrees Git. Dez skills independentes cobrem contexto, planejamento modular, handoffs, coordenação de agentes, deliberação entre pares e processos de engenharia no Codex e no Claude Code, com um único arquivo de instruções compartilhado. Os processos orientam os agentes a buscar o contexto relevante para cada tarefa.

## Contexto do projeto fora do repositório

Cada repositório ou monorepo tem um ambiente local. Seu mapa resumido ajuda os agentes a descobrir restrições aplicáveis e encontrar contexto relevante. O conhecimento útil fica em arquivos Markdown organizados por assunto. Planos temporários, configuração de equipe e contexto de continuação existem apenas quando necessários; pequenas correções solo dispensam registro de trabalho.

## Processos específicos e contexto delimitado

Planos macro são modulares independentemente da quantidade de agentes. Frentes de implementação e revisão podem referenciar os mesmos entregáveis, mantendo separados seus contextos de execução. Handoffs transferem responsabilidade por referências aos arquivos canônicos, sem copiar conversas.

Quando solicitada, a deliberação entre pares reúne agentes para desenvolver uma análise, decisão ou proposta. Os participantes contribuem e questionam ideias em igualdade, refinam uma síntese conjunta e preservam divergências relevantes. A coordenação organiza a troca sem determinar qual visão deve prevalecer.

## Dois hosts, um conjunto de instruções

Um único arquivo de instruções atende Codex e Claude Code: o Codex o lê diretamente, o Claude Code o importa, e cada host aplica uma seção curta própria. Mecânicas de host, como memória e worktrees gerenciadas, ficam a cargo do plugin; a pessoa define apenas escolhas práticas, como idioma, convenções de branch e política de testes.

## Worktrees e persistência segura

Worktrees criadas pelo Harness ficam dentro do ambiente do projeto; worktrees gerenciadas pelo host são aceitas onde estão. Agentes que colaboram em uma frente podem alternar a escrita; frentes independentes usam checkouts separados. O utilitário Python protege atualizações de Markdown contra a substituição de mudanças feitas depois da leitura.

Ao concluir um trabalho, o conhecimento útil é consolidado e os entregáveis que devem permanecer são preservados com referências atualizadas antes de mover o contexto temporário para a lixeira do ambiente, que a pessoa esvazia quando quiser. Material ainda necessário a outra frente ou a um handoff pendente permanece disponível. A retirada de uma worktree é uma decisão separada.
