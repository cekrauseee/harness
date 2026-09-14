---
description: >-
  Conhecimento persistente e coordenação de trabalho entre agentes, tarefas e
  repositórios.
metaDescription: >-
  O Continuity mantém decisões relevantes, descobertas úteis e trabalho pendente
  disponíveis entre tarefas com agentes. O conhecimento fica em arquivos
  Markdown locais, fora dos repositórios.
summary: >-
  O Continuity mantém decisões relevantes, descobertas úteis e trabalho pendente
  disponíveis entre tarefas com agentes. Desenvolvi o projeto para permitir que
  esse contexto acompanhe o trabalho quando ele passa para outra conversa ou
  outro executor. Quatro skills independentes orientam a configuração dos
  ambientes, a recuperação de contexto, a manutenção do conhecimento e a
  coordenação de alterações compartilhadas.
highlights:
  - conhecimento compartilhado entre projetos
  - arquivos Markdown locais, fora dos repositórios
  - recuperação orientada pela tarefa
  - coordenação de alterações compartilhadas
---

O Continuity mantém decisões relevantes, descobertas úteis e trabalho pendente disponíveis entre tarefas com agentes. Desenvolvi o projeto para permitir que esse contexto acompanhe o trabalho quando ele passa para outra conversa ou outro executor.

Quatro skills independentes orientam a configuração dos ambientes, a recuperação de contexto, a manutenção do conhecimento e a coordenação de alterações compartilhadas.

## Conhecimento compartilhado entre projetos

O conhecimento fica em arquivos Markdown locais, fora dos repositórios. Projetos relacionados podem pertencer a um mesmo ambiente e compartilhar notas e contribuições, preservando a identidade de cada pasta de trabalho.

Essa associação é explícita. Uma contribuição pode envolver arquivos de vários repositórios e continuar identificada pelo projeto em que começou. Worktrees compartilham o ambiente do repositório, mas mantêm identidades distintas como espaços de trabalho.

## Recuperação orientada pela tarefa

As skills orientam o agente a começar pelo pedido e pelas informações já disponíveis. O conhecimento salvo é consultado quando uma decisão anterior ou um fato ausente pode mudar a condução da tarefa.

As notas preservam escopo, fontes e incertezas. Uma decisão confirmada permanece distinta de uma hipótese, e informações já documentadas adequadamente no projeto podem continuar em sua fonte original.

## Coordenação de alterações e continuidade

Um utilitário em Python verifica reservas de arquivos que se sobrepõem e protege atualizações de conhecimento contra a substituição de uma versão que mudou desde a última leitura.

Quando uma tarefa precisa continuar depois, a contribuição guarda um resumo do estado atual e dos próximos passos. Na conclusão, o conhecimento relevante é consolidado e a contribuição é removida junto de suas reservas, em uma operação atômica.

As reservas coordenam agentes que seguem o mesmo procedimento. Elas não impedem alterações feitas por outros editores, uma limitação importante dessa forma de coordenação.
