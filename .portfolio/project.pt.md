---
description: "Continuidade baseada em arquivos para agentes que trabalham entre sessões e espaços de trabalho."
metaDescription: "Harness oferece identidade compartilhada de projeto, recuperação seletiva, contexto de tarefas, conhecimento com fontes e manutenção segura em arquivos locais."
summary: "Harness mantém o contexto útil de um projeto disponível entre sessões de agentes, sem colocar estado operacional no projeto nem carregar históricos completos de conversas."
highlights:
  - "Identidade de projeto"
  - "Recuperação seletiva"
  - "Contexto compartilhado de tarefas"
  - "Conhecimento com fontes"
  - "Manutenção segura"
  - "Git opcional"
---

## Produto

O trabalho com agentes costuma atravessar várias sessões, participantes e pastas. Harness oferece um registro canônico por projeto para identidade, conhecimento, responsabilidades, contribuições e checkpoints, armazenado fora do próprio projeto.

Projetos Git, pastas sem Git e worktrees são compatíveis. As worktrees compartilham o contexto do projeto, mas mantêm a procedência de cada espaço de trabalho, para que um agente encontre resultados anteriores sem presumir que outro checkout contenha os mesmos arquivos.

## O que construí

Projetei cinco skills agênticas para identidade de projetos, contexto seletivo, responsabilidade compartilhada, escrita de conhecimento e manutenção. Os agentes usam Markdown comum e as ferramentas já disponíveis; cada skill instalável de forma independente inclui o mesmo pequeno auxiliar transacional.

O modelo de tarefas registra responsabilidades e checkpoints dos agentes participantes. As reivindicações de escopo ajudam a detectar trabalhos sobrepostos, enquanto aceitação, commits e publicação continuam sendo decisões separadas, sustentadas por evidências próprias.

## Decisões de engenharia

Os agentes pesquisam e leem os documentos Markdown relevantes e decidem o que manter ou reescrever. Fontes, escopo, incertezas e datas importantes ficam em texto legível, sem motor de ranking, classificador ou esquema obrigatório de metadados para o conhecimento.

O auxiliar cuida da identidade do projeto, reservas atômicas, publicação do handoff atual e gravações conferidas contra o conteúdo observado. Seu sucesso confirma essas operações; investigar, julgar e verificar o resultado continua sendo trabalho do agente. Uma instrução curta no host conecta o fluxo sem hooks, daemon ou dependência de API externa.
