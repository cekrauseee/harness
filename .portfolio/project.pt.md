---
description: >-
  um jeito de manter o contexto de um projeto entre conversas com agentes.
metaDescription: >-
  o harness guarda o conhecimento de um projeto em arquivos markdown locais
  e ajuda agentes a retomar o trabalho, dividir tarefas e registrar o que ficou pendente.
summary: >-
  fiz o harness para que agentes possam retomar um projeto sem perder o
  contexto entre conversas e pastas de trabalho. as skills orientam a leitura
  e a atualização das notas, a divisão dos arquivos e o registro do que ficou
  pendente. um pequeno programa em python confere reservas e mudanças nos documentos.
highlights:
  - conhecimento do projeto em markdown
  - contexto compartilhado entre conversas e worktrees
  - reserva de arquivos para organizar o trabalho
  - notas e registros de trabalho atualizados
---

o harness dá aos agentes um lugar para guardar o que importa sobre um projeto:
decisões, descobertas úteis e trabalho que ainda precisa de atenção.

fiz isso com arquivos markdown comuns, guardados fora do projeto. ao começar
uma tarefa, o agente lê as notas relevantes e pode atualizá-las conforme o
trabalho avança. funciona com repositórios, worktrees e pastas sem git.

## retomar de onde parou

as skills orientam os agentes a buscar contexto, registrar o que aprenderam
e manter as notas úteis. as fontes e as dúvidas ficam junto da informação,
para que o próximo agente consiga distinguir uma decisão confirmada de uma
ideia que ainda está sendo explorada.

quando algo fica pela metade, o agente deixa um resumo para quem continuar.
quando termina, incorpora o que vale guardar às notas e remove os registros
de coordenação que já não servem.

## trabalhar nos mesmos arquivos

fiz um pequeno programa em python para cuidar das operações nos arquivos.
antes de editar, os agentes podem reservar o que vão usar e conferir se
outro agente está trabalhando ali. o programa também verifica se uma nota
mudou desde a leitura, antes de permitir que ela seja substituída.

essas reservas ajudam a organizar os agentes que seguem o processo. não
bloqueiam outros editores nem garantem que o trabalho esteja certo.
ler, pensar e conferir o resultado continua sendo responsabilidade do agente.
