---
description: >-
  conhecimento compartilhado para agentes trabalhando em vários projetos.
metaDescription: >-
  o continuity reúne projetos em ambientes compartilhados e mantém conhecimento,
  pendências e coordenação de arquivos em armazenamento local.
summary: >-
  fiz o continuity para manter decisões úteis e trabalho pendente disponíveis
  entre tarefas com agentes. os ambientes reúnem repositórios e pastas relacionados.
  quatro skills independentes orientam contexto, conhecimento e coordenação,
  com um pequeno programa em python protegendo as escritas compartilhadas.
highlights:
  - ambientes compartilhados por vários projetos
  - conhecimento em arquivos markdown locais
  - contexto buscado quando a tarefa precisa
  - reserva de arquivos e resumos para continuar o trabalho
---

o continuity, antes chamado harness, dá aos agentes um lugar para guardar
decisões, descobertas úteis e trabalho que ainda precisa de atenção. queria
que esse conhecimento acompanhasse o trabalho, para que outra conversa ou
outro agente pudesse retomá-lo.

fiz isso com arquivos markdown comuns, fora dos repositórios. quatro skills
independentes cuidam da configuração dos ambientes, da busca de contexto, das
notas úteis e da coordenação das escritas. o modelo, as ferramentas e o ambiente
de execução continuam sendo responsabilidade do aplicativo que usa as skills.

## projetos relacionados, um ambiente

um ambiente, chamado environment, reúne repositórios ou pastas que compartilham
conhecimento e trabalho. continuity e workflows podem formar um ambiente;
um portfólio e suas notas podem formar outro. cada pasta de trabalho mantém
sua identidade, inclusive nos worktrees, enquanto as notas e contribuições
ficam no ambiente compartilhado.

esse vínculo é explícito. projetos que já pertencem a ambientes diferentes
não são unidos silenciosamente. uma contribuição pode reservar arquivos em
vários repositórios e continuar identificando onde começou.

## buscar o contexto necessário

o agente começa com o pedido e as informações que já tem. busca conhecimento
salvo quando uma decisão anterior ou um fato que falta importa para a tarefa.
compartilhar um ambiente não significa carregar as notas de todos os projetos.

as notas preservam o escopo, as fontes e as dúvidas. uma decisão confirmada
continua distinta de uma ideia em discussão. o que já está bem documentado
no próprio projeto pode continuar lá.

## manter o trabalho em andamento

quando alguém precisa continuar uma tarefa, o agente deixa um resumo curto.
quando ela termina, incorpora o que vale guardar às notas e remove a contribuição.
mantive o foco no estado atual, sem um arquivo histórico de toda a atividade.

um pequeno programa em python confere reservas de arquivos que se sobrepõem
e protege notas contra substituições depois de uma mudança não observada.
ele também encerra uma contribuição concluída e libera suas reservas em uma
única operação atômica.

essas garantias ajudam os agentes que seguem o mesmo processo. não bloqueiam
outros editores nem avaliam a qualidade da implementação. o workflows pode
orientar a execução e a delegação; o continuity mantém o conhecimento e o
estado de coordenação disponíveis quando forem necessários.
